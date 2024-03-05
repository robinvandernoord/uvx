import sys
import textwrap
from pathlib import Path

import plumbum  # type: ignore
from plumbum.cmd import grep  # type: ignore

_uv = plumbum.local[sys.executable]["-m", "uv"]


def _run_python_in_venv(*args: str, venv: Path) -> str:
    python = venv / "bin" / "python"

    return plumbum.local[python](*args)


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
    executable = venv / "bin" / "python"
    return str(executable.resolve())  # /usr/bin/python3.xx


def get_package_version(package: str, venv: Path) -> str:
    """Get the currently installed version of a specific package."""
    # assumes `with virtualenv(venv)` block executing this function
    python = venv / "bin" / "python"

    regex = f"^({package}==|{package} @)"
    line: str = (plumbum.local[python]["-m", "uv"]["pip", "freeze"] | grep["-E", regex])().strip()
    return (line.split("@")[-1] if "@" in line else line.split("==")[-1]).strip()
