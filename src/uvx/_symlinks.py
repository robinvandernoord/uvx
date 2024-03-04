"""Symlink-related logic."""

import sys
import typing
from pathlib import Path
from typing import Optional

from ._constants import BIN_DIR, WORK_DIR
from ._python import run_python_code_in_venv

if typing.TYPE_CHECKING:
    from .metadata import Metadata


def install_symlink(symlink: str, venv: Path, force: bool = False, binaries: tuple[str, ...] = ()) -> bool:
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
        raw = run_python_code_in_venv(code, venv)
        return [_ for _ in raw.split("\n") if _]
    except Exception:
        return []


def install_symlinks(
    library: str,
    venv: Path,
    force: bool = False,
    binaries: tuple[str, ...] = (),
    meta: "Optional[Metadata]" = None,
) -> bool:
    """
    Install symlinks for a library in a virtual environment.

    Args:
        library (str): The name of the library.
        venv (Path): The path of the virtual environment.
        force (bool, optional): If True, overwrites existing symlinks. Defaults to False.
        binaries (tuple[str, ...], optional): The binaries to install. Defaults to ().
        meta: Optional metadata object to store results in

    Returns:
        bool: True if any symlink was installed, False otherwise.
    """
    symlinks = find_symlinks(library, venv)

    results = {}
    for symlink in symlinks:
        results[symlink] = install_symlink(symlink, venv, force=force, binaries=binaries)

    if meta:
        meta.scripts = results

    return any(results.values())


def check_symlink(symlink: str, venv: str) -> bool:
    """
    Check if a symlink is valid.

    This function checks if a symlink exists and if the target path is within the symlink's resolved parents.
    The symlink is considered valid if both conditions are met.

    Args:
        symlink (str): The name of the symlink to check.
        venv (str): The name of the virtual environment.

    Returns:
        bool: True if the symlink is valid, False otherwise.
    """
    symlink_path = BIN_DIR / symlink
    target_path = WORK_DIR / "venvs" / venv

    return symlink_path.is_symlink() and target_path in symlink_path.resolve().parents


def remove_symlink(symlink: str):
    """
    Remove a symlink.

    Args:
        symlink (str): The name of the symlink.
    """
    target_path = BIN_DIR / symlink
    if target_path.exists() and target_path.is_symlink():
        target_path.unlink(missing_ok=True)


def check_symlinks(symlinks: typing.Iterable[str], venv: str) -> dict[str, bool]:
    """
    Check all symlinks in the input iterable (e.g. list or dict.keys).

    Returns the key and whether the symlink is valid.
    """
    return {k: check_symlink(k, venv) for k in symlinks}
