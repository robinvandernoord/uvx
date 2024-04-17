"""Core functionality."""

import shutil
import subprocess  # nosec
import sys
import tempfile
import typing
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import plumbum  # type: ignore
import rich
from plumbum import local  # type: ignore
from result import Err, Ok, Result
from threadful import thread
from threadful.bonus import animate

from ._cli_support import interactive_selected_radio_value
from ._constants import WORK_DIR
from ._maybe import Maybe
from ._python import _uv, get_package_version, get_python_executable, get_python_version
from ._symlinks import find_symlinks, install_symlinks, remove_symlink
from .metadata import Metadata, collect_metadata, read_metadata, store_metadata


@thread
def uv(*args: typing.Any, **kwargs: str):
    """
    Execute the uv command with the provided arguments.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.

    Raises:
        NotImplementedError: If kwargs is not empty.

    Returns:
        str: The result of the uv command.
    """
    if kwargs:
        # todo: Add to args: {'a': 1, 'longer': 2} -> ['-a', '1', '--longer', '2']
        raise NotImplementedError("todo")

    result: str = _uv(*args)

    return result


@contextmanager
def virtualenv(virtualenv_dir: Path | str) -> typing.Generator[Path, None, None]:
    # https://github.com/tomerfiliba/plumbum/issues/168
    """
    Context manager for executing commands within the context of a Python virtualenv.

    Args:
        virtualenv_dir (Path | str): The directory of the virtual environment.

    Yields:
        Path: The path of the virtual environment.
    """
    old_path = local.env["PATH"]

    if not isinstance(virtualenv_dir, Path):
        virtualenv_dir = Path(virtualenv_dir)

    virtualenv_bin_dir = str((virtualenv_dir / "bin").resolve())
    new_path = "{}:{}".format(virtualenv_bin_dir, old_path)
    old_env = local.env.get("VIRTUAL_ENV")
    new_env = str(virtualenv_dir)
    local.env["PATH"] = new_path
    local.env["VIRTUAL_ENV"] = new_env
    old_python = local.python
    new_python = local["python"]
    local.python = new_python
    try:
        yield virtualenv_dir
    finally:
        local.env["PATH"] = old_path
        local.env["VIRTUAL_ENV"] = old_env
        local.python = old_python


@contextmanager
def as_virtualenv(venv_name: str) -> typing.Generator[Path, None, None]:
    """
    External variant of the 'virtualenv' context manager above.

    This variant takes in a venv name instead of a whole path.
    """
    workdir = ensure_local_folder()
    venv_path = workdir / "venvs" / venv_name
    with virtualenv(venv_path):
        yield venv_path


@contextmanager
def exit_on_pb_error() -> typing.Generator[None, None, None]:
    """Pass the plumbum error to the stderr and quit."""
    try:
        yield
    except plumbum.ProcessExecutionError as e:
        print(e.stderr, file=sys.stderr)
        exit(e.retcode)


def format_bools(data: dict[str, bool], sep=" | ") -> str:
    """Given a dictionary, format every format with the value True in green and False in red."""
    return sep.join([f"[green]{k}[/green]" if v else f"[red]{k}[/red]" for k, v in data.items()])


def _install_package(
    package_name: str, venv: Path | None, python: str | None, force: bool, no_cache: bool, extras: typing.Iterable[str]
) -> Result[Metadata, Exception]:
    match collect_metadata(package_name):
        case Err(e):
            return Err(e)
        case Ok(meta):
            # just bind meta
            ...

    if venv is None:
        venv = create_venv(meta.name, python=python, force=force)

    with virtualenv(venv), exit_on_pb_error():
        args: list[str] = []
        text = f"installing {meta.name}"
        if extras:
            args.extend(extras)
            text += f" with {extras}"

        if no_cache or force:
            args += ["--no-cache"]

        try:
            animate(uv("pip", "install", meta.install_spec, *args), text=text)

            # must still be in the venv and try for these:
            meta.installed_version = get_package_version(meta.name, venv)
            meta.python = get_python_version(venv)
            meta.python_raw = get_python_executable(venv)
            meta.injected = set(extras)

        except plumbum.ProcessExecutionError as e:
            remove_dir(venv)
            return Err(e)

    return Ok(meta)


def install_package(
    package_name: str,
    venv: Path | None = None,
    python: Optional[str] = None,
    force: bool = False,
    extras: Optional[typing.Iterable[str]] = None,
    no_cache: bool = False,
    skip_symlinks: bool = False,
) -> Result[str, Exception]:
    """
    Install a package in a virtual environment.

    Args:
        package_name (str): The name of the package.
        venv (Optional[Path], optional): The path of the virtual environment. Defaults to None.
        python (str): version or executable to use.
        force (bool, optional): If True, overwrites existing package. Defaults to False.
        extras: which optional features ('extras') to install for this package.
        no_cache: don't use `uv` cache.
        skip_symlinks: should symlinks NOT be set up after installing the package into a venv?
    """
    if extras is None:
        extras = []

    match _install_package(package_name, venv, python=python, extras=extras, force=force, no_cache=no_cache):
        case Err(err):
            return Err(err)
        case Ok(meta):
            ...

    if venv is None:
        venv = ensure_local_folder() / "venvs" / meta.name

    msg = ""
    if skip_symlinks or install_symlinks(meta.name, venv, force=force, meta=meta):
        msg = f"📦 {meta.name} ({meta.installed_version}) installed!"  # :package:

    store_metadata(meta, venv)
    return Ok(msg)


def reinstall_package(
    package_name: str,
    python: Optional[str] = None,
    force: bool = False,
    with_injected: bool = True,
    no_cache: bool = False,
) -> Result[str, Exception]:
    """
    Reinstalls a package in a virtual environment.

    This function first collects metadata about the package, then checks if the package is already installed in the
    virtual environment. If the package is not installed, it prompts the user to install it first. If the package is
    installed, it uninstalls the package and then reinstalls it. If a new version or extra is requested or no old
    metadata is available, it installs from the CLI argument package name. Otherwise, it installs from the old metadata
    spec. The Python version used for the virtual environment can be specified. If not specified, it uses the Python
    version from the existing metadata if available.

    Args:
        package_name (str): The name of the package to reinstall.
        python (Optional[str], optional): The Python version to use for the virtual environment. Defaults to None.
        force (bool, optional): If True, ignores if the virtual environment does not exist. Defaults to False.
        with_injected (bool): also re-include injected packages?
        no_cache: don't use `uv` cache.

    Raises:
        SystemExit: If the package is not installed in the virtual environment and force is False.
    """
    match collect_metadata(package_name):
        case Err(e):
            # can't work without metadata, just stop
            return Err(e)
        case Ok(new_metadata):
            # bind new_metadata
            ...

    workdir = ensure_local_folder()
    venv = workdir / "venvs" / new_metadata.name

    if not venv.exists() and not force:
        return Err(
            ValueError(
                f"'{new_metadata.name}' was not previously installed. Please run 'uvx install {package_name}' instead."
            )
        )

    existing_metadata = read_metadata(venv)

    # if a new version or extra is requested or no old metadata is available, install from cli arg package name.
    # otherwise, install from old metadata spec
    new_install_spec = bool(new_metadata.requested_version or new_metadata.extras)

    # install_spec = package_name if new_install_spec or not existing_metadata else existing_metadata.install_spec
    metadata: Optional[Metadata] = None
    match (new_install_spec, existing_metadata):
        case (False, Ok(metadata)):
            install_spec = metadata.install_spec
        case _:
            # if new install spec is True or there is no old metadata:
            install_spec = package_name

    # python = python or (existing_metadata.python_raw if existing_metadata else None)
    python = python or existing_metadata.map_or(None, lambda m: m.python_raw)

    uninstall_package(new_metadata.name, force=force)
    extras = metadata.injected if (with_injected and metadata and metadata.injected) else []
    return install_package(install_spec, python=python, force=force, extras=extras, no_cache=no_cache)


def inject_packages(into: str, package_specs: set[str]) -> Result[str, Exception]:
    """Install extra libraries into a package-specific venv."""
    match collect_metadata(into):
        case Err(e):
            return Err(e)
        case Ok(meta):
            # just bind meta
            ...

    workdir = ensure_local_folder()
    venv = workdir / "venvs" / meta.name

    if not venv.exists():
        return Err(ValueError(f"'{meta.name}' was not previously installed. Please run 'uvx install {into}' first."))

    # after getting the right venv, load actual metadata (with fallback to previous emptier metadata):
    meta = read_metadata(venv).unwrap_or(meta)

    with virtualenv(venv), exit_on_pb_error():
        try:
            animate(uv("pip", "install", *package_specs), text=f"injecting {package_specs}")
        except plumbum.ProcessExecutionError as e:
            return Err(e)

    meta.injected = (meta.injected or set()) | package_specs
    store_metadata(meta, venv)

    return Ok(f"💉 Injected {package_specs} into {meta.name}.")  # :needle:


def eject_packages(outof: str, package_specs: set[str]) -> Result[str, Exception]:
    """Uninstall extra libraries into a package-specific venv."""
    match collect_metadata(outof):
        case Err(e):
            return Err(e)
        case Ok(meta):
            # just bind meta
            ...

    workdir = ensure_local_folder()
    venv = workdir / "venvs" / meta.name

    if not venv.exists():
        return Err(ValueError(f"'{meta.name}' was not previously installed. Please run 'uvx install {outof}' first."))

    # after getting the right venv, load actual metadata (with fallback to previous emptier metadata):
    meta = read_metadata(venv).unwrap_or(meta)

    if not package_specs:
        package_specs = meta.injected or set()
        if not package_specs:
            return Err(ValueError("⚠️ No previous packages to uninject."))

    with virtualenv(venv), exit_on_pb_error():
        try:
            animate(uv("pip", "uninstall", *package_specs), text=f"ejecting {package_specs}")
        except plumbum.ProcessExecutionError as e:
            return Err(e)

    meta.injected = (meta.injected or set()) - package_specs
    store_metadata(meta, venv)

    return Ok(f"⏏️ Uninjected {package_specs} into {meta.name}.")  # :eject:


def remove_dir(path: Path):
    """
    Remove a directory.

    Args:
        path (Path): The path of the directory.
    """
    if path.exists():
        shutil.rmtree(path)


TMP = Path(tempfile.gettempdir())


def run_package(
    spec: str,
    args: list[str],
    keep: bool,
    python: Optional[str],
    no_cache: bool = False,
    binary_name: str = "",
) -> Result[str, Exception]:
    """Run a Python package in a temporary virtual environment."""
    # TemporaryDirectory with delete=False only works on py3.12 so do it manually:
    tmpdir = TMP / f"uvx-{spec}"
    try:
        _create_venv(tmpdir, python, with_pip=True)
        if keep:
            rich.print(f"ℹ️ Using virtualenv [blue]{tmpdir}[/blue]", file=sys.stderr)

        match _install_package(spec, tmpdir, python=python, no_cache=no_cache, force=False, extras=[]):
            case Err(msg):
                return Err(msg)
            case Ok(meta):
                ...

        tmp_bin = tmpdir / "bin"
        if binary_name:
            binary = tmp_bin / binary_name
        else:
            binary = tmp_bin / meta.name

        if not binary.exists():
            rich.print(f"Executable '{binary}' not found, looking for alternatives.", file=sys.stderr)

            symlinks = [tmp_bin / _ for _ in find_symlinks(meta.name, tmpdir)]
            symlinks = [_ for _ in symlinks if _.exists()]
            match len(symlinks):
                case 0:
                    return Err(ValueError("No alternative executables could be found."))
                case 1:
                    binary = symlinks[0]
                case _:
                    binary = Path(
                        interactive_selected_radio_value(
                            symlinks,  # type: ignore
                            prompt="Multiple executables found. "
                            "Please choose one (spacebar to select, enter to confirm):",
                        )
                    )

        subprocess.run([binary, *args])  # nosec

    finally:
        if not keep:
            remove_dir(tmpdir)

    return Ok("")


def upgrade_package(
    package_name: str, force: bool = False, skip_injected: bool = False, no_cache: bool = False
) -> Result[str, Exception]:
    """Upgrade a package in its venv."""
    # run `uv pip install --upgrade package` with requested install spec (version, extras, injected)
    # if --force is used, the previous version is ignored.
    match collect_metadata(package_name):
        case Err(e):
            return Err(e)
        case Ok(spec_metadata):
            # bind spec_metadata
            ...

    workdir = ensure_local_folder()
    venv = workdir / "venvs" / spec_metadata.name

    if not venv.exists():
        return Err(NotADirectoryError(f"No virtualenv for '{package_name}', stopping. Use 'uvx install' instead."))

    meta = read_metadata(venv).unwrap_or(spec_metadata)

    old_version = meta.installed_version

    with virtualenv(venv), exit_on_pb_error():
        # pip upgrade package[extras]==version *injected
        # if version spec in spec_metadata use that instead
        # if --force, drop version spec
        base_pkg = meta.name
        extras = meta.extras

        injected: set[str] = (not skip_injected and meta.injected) or set()
        # injected = set() if skip_injected else (meta.injected or set())

        version: str = spec_metadata.requested_version or (not force and meta.requested_version) or ""
        # version = spec_metadata.requested_version or ("" if force else meta.requested_version)

        options = []
        if no_cache or force:
            options.append("--no-cache")

        upgrade_spec = base_pkg + version
        if extras:
            upgrade_spec += "[" + ",".join(extras) + "]"

        try:
            animate(uv("pip", "install", "--upgrade", upgrade_spec, *injected, *options), text=f"upgrading {base_pkg}")
        except plumbum.ProcessExecutionError as e:
            return Err(e)

        meta.requested_version = version
        new_version = meta.installed_version = get_package_version(meta.name, venv)
        store_metadata(meta, venv)

    if old_version == new_version:
        msg = f"🌟 '{package_name}' is already up to date at version {new_version}!"
        if meta.requested_version:
            msg += (
                f"\n💡 This package was installed with a version constraint ({meta.requested_version}). "
                f"If you want to ignore this constraint, use `uvx upgrade --force {package_name}`."
            )

    else:
        msg = f"🚀 Successfully updated '{package_name}' from version {old_version} to version {new_version}!"

    return Ok(msg)


def uninstall_package(package_name: str, force: bool = False) -> Result[str, Exception]:
    """
    Uninstalls a package.

    Args:
        package_name (str): The name of the package.
        force (bool, optional): If True, ignores if the virtual environment does not exist. Defaults to False.
    """
    workdir = ensure_local_folder()
    venv_path = workdir / "venvs" / package_name

    if not venv_path.exists() and not force:
        escaped = package_name.replace("[", "\\[")
        return Err(
            NotADirectoryError(
                f"No virtualenv for '{escaped}', stopping. "
                f"Use '--force' to remove an executable with that name anyway.",
            )
        )

    meta = read_metadata(venv_path)

    symlinks = find_symlinks(package_name, venv_path) or [package_name]

    for symlink in symlinks:
        remove_symlink(symlink)

    remove_dir(venv_path)

    _version = meta.map_or("", lambda m: f" ({m.installed_version})")
    return Ok(_version)


def ensure_local_folder() -> Path:
    """
    Ensure the local folder exists.

    Returns:
        Path: The path of the local folder.
    """
    (WORK_DIR / "venvs").mkdir(exist_ok=True, parents=True)
    return WORK_DIR


def _create_venv(venv_path: Path, python: str | None, with_pip: bool):
    args = ["venv", venv_path]

    if python:
        args.extend(["--python", python])

    if with_pip:
        args.append("--seed")

    uv(*args).join()

    # if with_pip:
    #     with virtualenv(venv_path):
    #         animate(uv("pip", "install", "pip", "uv"))


def create_venv(name: str, python: Optional[str] = None, force: bool = False, with_pip: bool = True) -> Path:
    """
    Create a virtual environment.

    Args:
        name (str): The name of the virtual environment.
        python (str): which version of Python to use (e.g. 3.11, python3.11)
        force (bool): ignore existing venv
        with_pip (bool): also install (regular) pip into the venv? (required for `uvx runpip`)

    Returns:
        Path: The path of the virtual environment.
    """
    workdir = ensure_local_folder()

    venv_path = workdir / "venvs" / name

    if venv_path.exists() and not force:
        rich.print(
            f"'{name}' is already installed. "
            f"Use 'uvx upgrade' to update existing tools or pass '--force' to this command to ignore this message.",
            file=sys.stderr,
        )
        exit(1)

    _create_venv(venv_path, python, with_pip)

    return venv_path


def list_packages() -> typing.Generator[tuple[str, Maybe[Metadata]], None, None]:
    """Iterate through all uvx venvs and load the metadata files one-by-one."""
    workdir = ensure_local_folder()

    for subdir in workdir.glob("venvs/*"):
        metadata = read_metadata(subdir)

        yield subdir.name, metadata


def run_command(command: str, *args: str, printfn: typing.Callable[..., None] = print) -> int:
    """Run a command via plumbum without raising an error on exception."""
    # retcode = None makes the command not raise an exception on error:
    exit_code, stdout, stderr = plumbum.local[command][args].run(retcode=None)

    if stdout:
        printfn(stdout.strip())
    if stderr:
        printfn(stderr.strip(), file=sys.stderr)
    return exit_code
