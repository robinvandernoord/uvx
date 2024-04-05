"""This file builds the Typer cli."""

import os
import subprocess  # nosec
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import rich
import typer
from result import Err, Ok, Result
from typer import Context

from uvx._constants import BIN_DIR

from .__about__ import __version__
from ._maybe import Maybe
from ._python import _python_in_venv, _uv
from .core import (
    as_virtualenv,
    format_bools,
    inject_packages,
    install_package,
    list_packages,
    reinstall_package,
    run_command,
    uninstall_package,
    upgrade_package,
)
from .metadata import Metadata

app = typer.Typer()


def output(result: Result[str, Exception]) -> None:
    match result:
        case Ok(msg):
            rich.print(msg)  # :trash:
        case Err(err):
            rich.print(err, file=sys.stderr)


@app.command()
def install(package_name: str, force: bool = False, python: str = "", no_cache: bool = False):
    """Install a package (by pip name)."""
    # todo: support 'install .'
    output(install_package(package_name, python=python, force=force, no_cache=no_cache))


@app.command(name="upgrade")
@app.command(name="update")
def upgrade(package_name: str, force: bool = False, skip_injected: bool = False, no_cache: bool = False):
    output(upgrade_package(package_name, force=force, skip_injected=skip_injected, no_cache=no_cache))


@app.command(name="remove")
@app.command(name="uninstall")
def uninstall(package_name: str, force: bool = False):
    """Uninstall a package (by pip name)."""
    output(uninstall_package(package_name, force=force).map(lambda version: f"🗑️ {package_name}{version} removed!"))


@app.command()
def reinstall(
    package: str,
    python: Optional[str] = None,
    force: bool = False,
    without_injected: bool = False,
    no_cache: bool = False,
):
    """Uninstall a package (by pip name) and re-install from the original spec (unless a new spec is supplied)."""
    output(
        reinstall_package(
            package,
            python=python,
            force=force,
            with_injected=not without_injected,
            no_cache=no_cache,
        ).map(lambda _: _.replace(" installed", " reinstalled"))
    )


@app.command()
def inject(into: str, package_specs: list[str]):
    output(
        inject_packages(
            into,
            set(package_specs),
        )
    )


# list
def _list_short(name: str, metadata: Maybe[Metadata]):
    rich.print("-", name, metadata.map_or("[red]?[/red]", lambda md: md.installed_version))


TAB = " " * 3


def _list_normal(name: str, metadata: Maybe[Metadata], verbose: bool = False):
    match metadata:
        case Err(_):
            print("-", name)
            rich.print(TAB, "[red]Missing metadata [/red]")
            return
        case Ok(md):
            # just binds 'md'
            pass

    extras = list(md.extras)
    name_with_extras = name if not extras else f"{name}{extras}"
    rich.print("-", name_with_extras)

    md.check_script_symlinks(name)

    if verbose:
        rich.print(TAB, str(md))
    else:
        rich.print(
            TAB,
            f"Installed Version: {md.installed_version} on {md.python}.",
        )
        if md.injected:
            p = ", ".join([f"'{_}'" for _ in md.injected])
            rich.print(TAB, f"Injected Packages: {p}")
        rich.print(TAB, "Scripts:", format_bools(md.scripts))


def _list_venvs_json():
    from json import dumps

    print(
        dumps(
            {
                name: metadata.map_or({}, lambda md: md.check_script_symlinks(name).to_dict())
                for name, metadata in list_packages()
            },
            indent=2,
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
        python = _python_in_venv(venv_path)
        run_command(str(python), "-m", "uv", *ctx.args)  # run_command does not work with _uv_in_venv !


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def runpip(venv: str, ctx: Context):
    """Run 'pip' in the right venv."""
    with as_virtualenv(venv):
        run_command("pip", *ctx.args)


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def runpython(venv: str, ctx: Context):
    """Run 'python' in the right venv."""
    with as_virtualenv(venv) as venv_path:
        python = venv_path / "bin" / "python"
        subprocess.run([python, *ctx.args])  # nosec


# todo:
# self-upgrade (uv and uvx)
# upgrade-all


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
    run_command(str(_uv), "--version", printfn=rich.print)
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
