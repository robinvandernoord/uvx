"""Core functionality."""

import shutil
import sys
import textwrap
import typing
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import plumbum  # type: ignore
from plumbum import local  # type: ignore
from plumbum.cmd import uv as _uv  # type: ignore
from threadful import thread
from threadful.bonus import animate

BIN_DIR = Path.home() / ".local/bin"


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
    old_env = local.env["VIRTUAL_ENV"]
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
def exit_on_pb_error() -> typing.Generator[None, None, None]:
    """Pass the plumbum error to the stderr and quit."""
    try:
        yield
    except plumbum.ProcessExecutionError as e:
        print(e.stderr, file=sys.stderr)
        exit(e.retcode)


def run_python_in_venv(code: str, venv: Path) -> str:
    """
    Run Python code in a virtual environment.

    Args:
        code (str): The Python code to run.
        venv (Path): The path of the virtual environment.

    Returns:
        str: The output of the Python code.
    """
    python = venv / "bin" / "python"

    code = textwrap.dedent(code)
    return plumbum.local[python]("-c", code)


def find_symlinks(library: str, venv: Path) -> list[str]:
    """
    Find the symlinks for a library in a virtual environment.

    Args:
        library (str): The name of the library.
        venv (Path): The path of the virtual environment.

    Returns:
        list: The list of symlinks.
    """
    code = f"""
    import importlib.metadata

    for script in importlib.metadata.distribution('{library}').entry_points:
        if script.group != "console_scripts":
            continue

        print(script.name)
    """

    try:
        raw = run_python_in_venv(code, venv)
        return [_ for _ in raw.split("\n") if _]
    except Exception:
        return []


def install_symlink(
    symlink: str, venv: Path, force: bool = False, binaries: tuple[str, ...] = ()
) -> bool:
    """
    Install a symlink in the virtual environment.

    Args:
        symlink (str): The name of the symlink.
        venv (Path): The path of the virtual environment.
        force (bool, optional): If True, overwrites existing symlink. Defaults to False.
        binaries (tuple[str, ...], optional): The binaries to install. Defaults to ().

    Returns:
        bool: True if the symlink was installed, False otherwise.
    """
    if binaries and symlink not in binaries:
        return False

    target_path = BIN_DIR / symlink

    if target_path.exists():
        if force:
            target_path.unlink()
        else:
            print(
                f"Script {symlink} already exists in {BIN_DIR}. Use --force to ignore this warning.",
                file=sys.stderr,
            )
            return False

    symlink_path = venv / "bin" / symlink
    if not symlink_path.exists():
        print(
            f"Could not symlink {symlink_path} because the script didn't exist.",
            file=sys.stderr,
        )
        return False

    target_path.symlink_to(symlink_path)
    return True


def install_symlinks(
    library: str, venv: Path, force: bool = False, binaries: tuple[str, ...] = ()
) -> bool:
    """
    Install symlinks for a library in a virtual environment.

    Args:
        library (str): The name of the library.
        venv (Path): The path of the virtual environment.
        force (bool, optional): If True, overwrites existing symlinks. Defaults to False.
        binaries (tuple[str, ...], optional): The binaries to install. Defaults to ().

    Returns:
        bool: True if any symlink was installed, False otherwise.
    """
    symlinks = find_symlinks(library, venv)

    results = []
    for symlink in symlinks:
        results.append(install_symlink(symlink, venv, force=force, binaries=binaries))

    return any(results)


def install_package(
    package_name: str, venv: Optional[Path] = None, force: bool = False
):
    """
    Install a package in a virtual environment.

    Args:
        package_name (str): The name of the package.
        venv (Optional[Path], optional): The path of the virtual environment. Defaults to None.
        force (bool, optional): If True, overwrites existing package. Defaults to False.
    """
    if venv is None:
        venv = create_venv(package_name)

    with virtualenv(venv), exit_on_pb_error():
        animate(
            uv("pip", "install", package_name),
            # text=f"installing {package_name}"
        )

    if install_symlinks(package_name, venv, force=force):
        print(f"📦 {package_name} installed!")


def remove_symlink(symlink: str):
    """
    Remove a symlink.

    Args:
        symlink (str): The name of the symlink.
    """
    target_path = BIN_DIR / symlink
    if target_path.exists() and target_path.is_symlink():
        target_path.unlink(missing_ok=True)


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

    if not venv_path.exists() and not force:
        print(
            f"No virtualenv for {package_name}, stopping. Use --force to remove an executable with that name anyway.",
            file=sys.stderr,
        )
        exit(1)

    symlinks = find_symlinks(package_name, venv_path) or [package_name]

    for symlink in symlinks:
        remove_symlink(symlink)

    remove_dir(venv_path)
    print(f"🗑️ {package_name} removed!")


def ensure_local_folder() -> Path:
    """
    Ensure the local folder exists.

    Returns:
        Path: The path of the local folder.
    """
    workdir = Path("~/.local/uvx/").expanduser()
    (workdir / "venvs").mkdir(exist_ok=True, parents=True)
    return workdir


def create_venv(name: str) -> Path:
    """
    Create a virtual environment.

    Args:
        name (str): The name of the virtual environment.

    Returns:
        Path: The path of the virtual environment.
    """
    workdir = ensure_local_folder()

    venv_path = workdir / "venvs" / name

    uv("venv", venv_path).join()

    return venv_path
