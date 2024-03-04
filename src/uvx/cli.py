"""This file builds the Typer cli."""

import os
import subprocess  # nosec
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import plumbum  # type: ignore
import rich
import typer
from typer import Context

from uvx._constants import BIN_DIR

from .__about__ import __version__
from .core import (
    as_virtualenv,
    format_bools,
    install_package,
    list_packages,
    reinstall_package,
    run_command,
    uninstall_package,
)
from .metadata import Metadata

app = typer.Typer()


@app.command()
def install(package_name: str, force: bool = False, python: str = ""):
    """Install a package (by pip name)."""
    # todo: support 'install .'
    install_package(package_name, python=python, force=force)


@app.command(name="remove")
@app.command(name="uninstall")
def uninstall(package_name: str, force: bool = False):
    """Uninstall a package (by pip name)."""
    uninstall_package(package_name, force=force)


@app.command()
def reinstall(package: str, python: Optional[str] = None, force: bool = False):
    """Uninstall a package (by pip name) and re-install from the original spec (unless a new spec is supplied)."""
    reinstall_package(package, python=python, force=force)


# list
def _list_short(name: str, metadata: Optional[Metadata]):
    rich.print("-", name, metadata.installed_version if metadata else "[red]?[/red]")


TAB = " " * 3


def _list_normal(name: str, metadata: Optional[Metadata], verbose: bool = False):
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


def _list_venvs_json():
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
    """List packages and apps installed with uvx."""
    if json:
        return _list_venvs_json()

    for name, metadata in list_packages():
        if short:
            _list_short(name, metadata)
        else:
            _list_normal(name, metadata, verbose=verbose)



@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def runuv(venv: str, ctx: Context):
    """Run 'uv' in the right venv."""
    with as_virtualenv(venv) as venv_path:
        python = venv_path / "bin" / "python"
        run_command(str(python), "-m", "uv", *ctx.args)


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def runpip(venv: str, ctx: Context):
    """Run 'pip' in the right venv."""
    with as_virtualenv(venv) as venv_path:
        python = venv_path / "bin" / "python"
        plumbum.local[str(python)]("-m", "uv", "pip", "install", "pip")
        run_command("pip", *ctx.args)


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def runpython(venv: str, ctx: Context):
    """Run 'python' in the right venv."""
    with as_virtualenv(venv) as venv_path:
        python = venv_path / "bin" / "python"
        subprocess.run([python, *ctx.args])  # nosec


# upgrade

# self-upgrade (uv and uvx)

# inject

# version or --version (incl. 'uv' version and Python version)

# ...


def add_to_bashrc(text: str, with_comment: bool = True):
    """Add text to ~/.bashrc, usually with a comment (uvx + timestamp)."""
    with (Path.home() / ".bashrc").resolve().open("a") as f:
        now = str(datetime.now()).split(".")[0]
        final_text = "\n"
        final_text += f"# Added by `uvx` at {now}\n" if with_comment else ""
        final_text += text + "\n"
        f.write(final_text)


@app.command()
def ensurepath(force: bool = False):
    """Update ~/.bashrc with a PATH that includes the local bin directory that uvx uses."""
    env_path = os.getenv("PATH", "")
    bin_in_path = str(BIN_DIR) in env_path.split(":")

    if bin_in_path and not force:
        rich.print(
            f"[yellow]{BIN_DIR} is already added to your path. Use '--force' to add it to your .bashrc file anyway.[/yellow]"
        )
        exit(1)

    add_to_bashrc(f'export PATH="$PATH:{BIN_DIR}"')


@app.command()
def completions():  # noqa
    """
    Use --install-completion to install the autocomplete script, \
        or --show-completion to see what would be installed.
    """
    rich.print("Use 'uvx --install-completion' to install the autocomplete script to your '.bashrc' file.")


def version_callback():
    """Show the current versions when running with --version."""
    rich.print("uvx", __version__)
    run_command(sys.executable, "-m", "uv", "--version", printfn=rich.print)
    rich.print("Python", sys.version.split(" ")[0])


@app.callback(invoke_without_command=True, no_args_is_help=True)
def main(
    ctx: typer.Context,
    # stops the program:
    version: bool = False,
) -> None:  # noqa
    """
    This callback will run before every command, setting the right global flags.

    Args:
        ctx: context to determine if a subcommand is passed, etc

        version: display current version?

    """
    if version:
        version_callback()
    elif not ctx.invoked_subcommand:
        rich.print("[yellow]Missing subcommand. Try `uvx --help` for more info.[/yellow]")
    # else: just continue


if __name__ == "__main__":  # pragma: no cover
    app()
