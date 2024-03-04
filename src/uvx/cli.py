"""This file builds the Typer cli."""

import os
import subprocess
import sys
from typing import Optional

import plumbum
import rich
import typer
from typer import Context

from .core import (
    as_virtualenv,
    ensure_local_folder,
    format_bools,
    install_package,
    list_packages,
    reinstall_package,
    run_command,
    uninstall_package,
    uv,
    virtualenv,
)
from .metadata import Metadata, read_metadata

app = typer.Typer()


@app.command()
def install(package_name: str, force: bool = False, python: str = None):
    """Install a package (by pip name)."""
    install_package(package_name, python=python, force=force)


@app.command(name="remove")
@app.command(name="uninstall")
def uninstall(package_name: str, force: bool = False):
    """Uninstall a package (by pip name)."""
    uninstall_package(package_name, force=force)


@app.command()
def reinstall(package: str, python: Optional[str] = None, force: bool = False):
    reinstall_package(package, python=python, force=force)


# list
def list_short(name: str, metadata: Optional[Metadata]):
    rich.print("-", name, metadata.installed_version if metadata else "[red]?[/red]")


TAB = " " * 3


def list_normal(name: str, metadata: Optional[Metadata], verbose: bool = False):
    if not metadata:
        print("-", name)
        rich.print(TAB, "[red]Missing metadata [/red]")
        return
    else:
        extras = list(metadata.extras)
        name_with_extras = name if not extras else f"{name}{extras}"
        print("-", name_with_extras)

    metadata.check_script_symlinks(name)

    if verbose:
        rich.print(TAB, metadata)
    else:
        rich.print(
            TAB,
            f"Installed Version: {metadata.installed_version} on {metadata.python}.",
        )
        rich.print(TAB, "Scripts:", format_bools(metadata.scripts))


def list_venvs_json():
    from json import dumps

    print(
        dumps(
            {
                name: metadata.check_script_symlinks(name).to_dict() if metadata else {}
                for name, metadata in list_packages()
            }
        )
    )


@app.command(name="list")
def list_venvs(short: bool = False, verbose: bool = False, json: bool = False):
    """
    List packages and apps installed with uvx.
    """

    if json:
        return list_venvs_json()

    for name, metadata in list_packages():
        if short:
            list_short(name, metadata)
        else:
            list_normal(name, metadata, verbose=verbose)


# run


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def runuv(venv: str, ctx: Context):
    with as_virtualenv(venv):
        run_command("uv", *ctx.args)


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def runpip(venv: str, ctx: Context):
    with as_virtualenv(venv):
        plumbum.local["uv"]("pip", "install", "pip")
        run_command("pip", *ctx.args)


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def runpython(venv: str, ctx: Context):
    with as_virtualenv(venv) as venv_path:
        python = venv_path / "bin" / "python"
        subprocess.run([python, *ctx.args])


# upgrade

# self-upgrade (uv and uvx)

# inject

# version or --version (incl. 'uv' version and Python version)

# ...
