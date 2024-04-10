import sys
import textwrap
import typing
from pathlib import Path

import plumbum  # type: ignore
from plumbum.cmd import grep  # type: ignore
from plumbum.commands.base import BoundCommand  # type: ignore
from plumbum.machines.local import LocalCommand  # type: ignore
from uv import find_uv_bin

_python = plumbum.local[sys.executable]
_pip = _python["-m", "pip"]
_uv = plumbum.local[find_uv_bin()]


def _python_in_venv(venv: Path) -> LocalCommand:
    python = venv / "bin" / "python"
    return plumbum.local[python]


def _uv_in_venv(venv: Path):
    python = _python_in_venv(venv)
    return python["-m", "uv"]


def _run_python_in_venv(*args: str, venv: Path) -> str:
    python = _python_in_venv(venv)

    return python(*args)


def run_python_code_in_venv(code: str, venv: Path) -> str:
    """
    Run Python code in a virtual environment.

    Args:
        code (str): The Python code to run.
        venv (Path): The path of the virtual environment.

    Returns:
        str: The output of the Python code.
    """
    code = textwrap.dedent(code)
    return _run_python_in_venv("-c", code, venv=venv)


def get_python_version(venv: Path):
    """Get the reported (human-readable) version of Python installed in a venv."""
    return _run_python_in_venv("--version", venv=venv).strip()


def get_python_executable(venv: Path):
    """Get the Python executable for a venv (used to determine the version)."""
    executable = venv / "bin" / "python"  # DON'T use _python_in_venv because we want to resolve the symlink:
    return str(executable.resolve())  # /usr/bin/python3.xx


T = typing.TypeVar("T")

RAISE = object()  # special sentry object


def _get_package_version(package: str, pip_list: BoundCommand, default: T) -> str | T:
    try:
        regex = f"^({package}==|{package} @)"
        line: str = (pip_list | grep["-E", regex])().strip()
        return (line.split("@")[-1] if "@" in line else line.split("==")[-1]).strip()
    except Exception as e:
        if default is RAISE:
            raise e

        return default


def get_package_version(package: str, venv: Path) -> str:
    """Get the currently installed version of a specific package."""
    # assumes `with virtualenv(venv)` block executing this function
    uv = _uv_in_venv(venv)

    return _get_package_version(
        package,
        uv["pip", "freeze"],
        default="",
    )
