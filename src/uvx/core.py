"""Core functionality."""

import shutil
import sys
import typing
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import plumbum  # type: ignore
import rich
from plumbum import local  # type: ignore
from threadful import thread
from threadful.bonus import animate

from ._constants import WORK_DIR
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


def install_package(
    package_name: str,
    venv: Optional[Path] = None,
    python: Optional[str] = None,
    force: bool = False,
):
    """
    Install a package in a virtual environment.

    Args:
        package_name (str): The name of the package.
        venv (Optional[Path], optional): The path of the virtual environment. Defaults to None.
        force (bool, optional): If True, overwrites existing package. Defaults to False.
    """
    meta = collect_metadata(package_name)

    if venv is None:
        venv = create_venv(meta.name, python=python, force=force)

    with virtualenv(venv), exit_on_pb_error():
        try:
            animate(uv("pip", "install", package_name), text=f"installing {meta.name}")

            # must still be in the venv for these:
            meta.installed_version = get_package_version(meta.name)
            meta.python = get_python_version(venv)
            meta.python_raw = get_python_executable(venv)

        except plumbum.ProcessExecutionError as e:
            remove_dir(venv)
            raise e

    if install_symlinks(meta.name, venv, force=force, meta=meta):
        rich.print(f"📦 {meta.name} ({meta.installed_version}) installed!")  # :package:

    store_metadata(meta, venv)


def reinstall_package(package_name: str, python: Optional[str] = None, force: bool = False):
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

    Raises:
        SystemExit: If the package is not installed in the virtual environment and force is False.
    """
    new_metadata = collect_metadata(package_name)

    workdir = ensure_local_folder()
    venv = workdir / "venvs" / new_metadata.name

    if not venv.exists():
        rich.print(
            f"'{new_metadata.name}' was not previously installed. " f"Please run 'uvx install {package_name}' instead."
        )
        exit(1)

    existing_metadata = read_metadata(venv)

    # if a new version or extra is requested or no old metadata is available, install from cli arg package name.
    # otherwise, install from old metadata spec
    new_install_spec = bool(new_metadata.requested_version or new_metadata.extras)
    install_spec = package_name if new_install_spec or not existing_metadata else existing_metadata.install_spec

    python = python or (existing_metadata.python_raw if existing_metadata else None)

    uninstall_package(new_metadata.name, force=force)
    install_package(install_spec, python=python, force=force)


def remove_dir(path: Path):
    """
    Remove a directory.

    Args:
        path (Path): The path of the directory.
    """
    if path.exists():
        shutil.rmtree(path)


def uninstall_package(package_name: str, force: bool = False):
    """
    Uninstalls a package.

    Args:
        package_name (str): The name of the package.
        force (bool, optional): If True, ignores if the virtual environment does not exist. Defaults to False.
    """
    workdir = ensure_local_folder()
    venv_path = workdir / "venvs" / package_name

    meta = read_metadata(venv_path)

    if not venv_path.exists() and not force:
        rich.print(
            f"No virtualenv for '{package_name}', stopping. Use '--force' to remove an executable with that name anyway.",
            file=sys.stderr,
        )
        exit(1)

    symlinks = find_symlinks(package_name, venv_path) or [package_name]

    for symlink in symlinks:
        remove_symlink(symlink)

    remove_dir(venv_path)

    _version = f" ({meta.installed_version})" if meta else ""
    rich.print(f"🗑️ {package_name}{_version} removed!")  # :trash:


def ensure_local_folder() -> Path:
    """
    Ensure the local folder exists.

    Returns:
        Path: The path of the local folder.
    """
    (WORK_DIR / "venvs").mkdir(exist_ok=True, parents=True)
    return WORK_DIR


def create_venv(name: str, python: Optional[str] = None, force: bool = False) -> Path:
    """
    Create a virtual environment.

    Args:
        name (str): The name of the virtual environment.
        python (str): which version of Python to use (e.g. 3.11, python3.11)
        force (bool): ignore existing venv

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

    args = ["venv", venv_path]

    if python:
        args.extend(["--python", python])

    uv(*args).join()

    return venv_path


def list_packages() -> typing.Generator[tuple[str, Metadata | None], None, None]:
    """Iterate through all uvx venvs and load the metadata files one-by-one."""
    workdir = ensure_local_folder()

    for subdir in workdir.glob("venvs/*"):
        metadata = read_metadata(subdir)

        yield subdir.name, metadata


def run_command(command: str, *args: str, printfn: typing.Callable[..., None] = print):
    """Run a command via plumbum without raising an error on exception."""
    # retcode = None makes the command not raise an exception on error:
    exit_code, stdout, stderr = plumbum.local[command][args].run(retcode=None)

    if stdout:
        printfn(stdout.strip())
    if stderr:
        printfn(stderr.strip(), file=sys.stderr)
    return exit_code
