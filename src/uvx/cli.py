"""This file builds the Typer cli."""

import functools
import os
import platform
import subprocess  # nosec
import sys
import typing
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import plumbum as pb  # type: ignore
import rich
import typer
from plumbum import local
from plumbum.commands.base import BoundCommand  # type: ignore
from result import Err, Ok, Result
from typer import Context

from .__about__ import __version__
from ._cli_support import State
from ._constants import BIN_DIR
from ._maybe import Maybe
from ._python import _get_package_version, _pip, _python_in_venv, _uv
from .core import (
    as_virtualenv,
    eject_packages,
    format_bools,
    inject_packages,
    install_package,
    list_packages,
    reinstall_package,
    run_command,
    run_package,
    uninstall_package,
    upgrade_package,
)
from .metadata import Metadata

app = typer.Typer()
state = State()


def output(result: Result[str, Exception]) -> None:
    """Output positive (ok) result to stdout and error result to stderr."""
    match result:
        case Ok(msg):
            if msg:
                rich.print(msg)
        case Err(err):
            rich.print(err, file=sys.stderr)


OPTION_PYTHON_HELP_TEXT = "Python version or executable to use, e.g. `3.12`, `python3.12`, `/usr/bin/python3.12`"


@app.command()
def install(
    package_name: str,
    force: Annotated[
        bool,
        typer.Option(
            "-f", "--force", help="Overwrite currently installed executables with the same name (in ~/.local/bin)"
        ),
    ] = False,
    python: Annotated[str, typer.Option(help=OPTION_PYTHON_HELP_TEXT)] = "",
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Run without `uv` cache")] = False,
):
    """Install a package (by pip name)."""
    output(install_package(package_name, python=python, force=force, no_cache=no_cache))


@app.command(name="upgrade")
@app.command(name="update")
def upgrade(
    package_name: str,
    force: Annotated[bool, typer.Option("-f", "--force", help="Ignore previous version constraint")] = False,
    skip_injected: Annotated[
        bool, typer.Option("--skip-injected", help="Don't also upgrade injected packages")
    ] = False,
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Run without `uv` cache")] = False,
):
    """Upgrade a package."""
    output(upgrade_package(package_name, force=force, skip_injected=skip_injected, no_cache=no_cache))


@app.command()
def upgrade_all(
    force: Annotated[bool, typer.Option("-f", "--force", help="Ignore previous version constraint")] = False,
    skip_injected: Annotated[
        bool, typer.Option("--skip-injected", help="Don't also upgrade injected packages")
    ] = False,
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Run without `uv` cache")] = False,
):
    """Upgrade all uvx-installed packages."""
    for venv_name, _ in list_packages():
        upgrade(venv_name, force=force, skip_injected=skip_injected, no_cache=no_cache)


@app.command(name="remove")
@app.command(name="uninstall")
def uninstall(
    package_name: str,
    force: Annotated[
        bool,
        typer.Option(
            "-f",
            "--force",
            help="Remove executable with the same name (in ~/.local/bin) even if related venv was not found",
        ),
    ] = False,
):
    """Uninstall a package (by pip name)."""
    output(uninstall_package(package_name, force=force).map(lambda version: f"🗑️ {package_name}{version} removed!"))


@app.command()
def uninstall_all(
    force: Annotated[
        bool,
        typer.Option(
            "-f",
            "--force",
            help="Remove executable with the same name (in ~/.local/bin) even if related venv was not found",
        ),
    ] = False,
):
    """Uninstall all uvx-installed packages."""
    for venv_name, _ in list_packages():
        uninstall(venv_name, force=force)


@app.command()
def reinstall(
    package: str,
    python: Annotated[str, typer.Option(help=OPTION_PYTHON_HELP_TEXT)] = "",
    force: Annotated[bool, typer.Option("-f", "--force", help="See `install --force`")] = False,
    without_injected: Annotated[
        bool, typer.Option("--without-injected", help="Don't include previously injected libraries in reinstall")
    ] = False,
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Run without `uv` cache")] = False,
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
def reinstall_all(
    python: Annotated[str, typer.Option(help=OPTION_PYTHON_HELP_TEXT)] = "",
    force: Annotated[bool, typer.Option("-f", "--force", help="See `install --force`")] = False,
    without_injected: Annotated[
        bool, typer.Option("--without-injected", help="Don't include previously injected libraries in reinstall")
    ] = False,
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Run without `uv` cache")] = False,
):
    """Uninstall all uvx-installed packages."""
    for venv_name, _ in list_packages():
        reinstall(venv_name, python=python, force=force, without_injected=without_injected, no_cache=no_cache)


@app.command()
def inject(into: str, package_specs: list[str]):
    """Install additional packages to a virtual environment managed by uvx."""
    output(
        inject_packages(
            into,
            set(package_specs),
        )
    )


@app.command(name="eject")
@app.command(name="uninject")
def uninject(
    outof: str,
    package_specs: typing.Annotated[list[str], typer.Argument()] = None,  # type: ignore
):
    """Uninstall additional packages from a virtual environment managed by uvx."""
    output(
        eject_packages(
            outof,
            set(package_specs or []),
        )
    )


UVX2_PLATFORMS = {"linux"}
UVX2_ARCH = {"x86_64", "aarch64"}


def system_supports_uvx2() -> bool:
    return sys.platform in UVX2_PLATFORMS and platform.machine() in UVX2_ARCH


def _uvx_upgrade_spec():
    # uvx 2.x should only be used on supported platforms.
    return "uvx" if system_supports_uvx2() else "uvx<2"


def _self_update_via_cmd(pip_ish: BoundCommand, with_uv: bool):
    old = {}
    new = {}

    old["uv"] = _get_package_version("uv", pip_ish["freeze"], default="unknown")

    old["uvx"] = _get_package_version("uvx", pip_ish["freeze"], default="unknown")

    cmd = pip_ish["install", "--upgrade", _uvx_upgrade_spec()]
    if with_uv:
        cmd = cmd["uv"]

    cmd()

    new["uv"] = _get_package_version("uv", pip_ish["freeze"], default="unknown")

    new["uvx"] = _get_package_version("uvx", pip_ish["freeze"], default="unknown")

    return old, new


def _self_update_via_uv(with_uv: bool):
    return _self_update_via_cmd(_uv["pip", "--no-cache"], with_uv=with_uv)


def _self_update_via_pip(with_uv: bool):
    return _self_update_via_cmd(_pip["--no-cache-dir"], with_uv=with_uv)


@app.command()
def self_update(
    with_uv: Annotated[bool, typer.Option("--with-uv/--without-uv", "-w/-W")] = True,
):
    """Update the current installation of uvx and optionally uv."""
    # if in venv and uv available -> upgrade via uv
    # else: upgrade via pip

    try:
        if os.getenv("VIRTUAL_ENV"):
            # already activated venv
            old, new = _self_update_via_uv(with_uv=with_uv)
        elif sys.prefix != sys.base_prefix:
            # venv-like environment (pipx, uvx)
            with local.env(VIRTUAL_ENV=sys.prefix):
                old, new = _self_update_via_uv(with_uv=with_uv)
        else:
            old, new = _self_update_via_pip(with_uv=with_uv)

    except pb.ProcessExecutionError as e:
        print(e.message, file=sys.stdout)
        print(e.stdout, file=sys.stdout)
        print(e.stderr, file=sys.stderr)
        exit(e.retcode)

    for package, old_version in old.items():
        new_version = new.get(package)
        if new_version == old_version:
            rich.print(f"🌟 [bold]'{package}'[/bold] not updated (version: [green]{old_version}[/green])")
        else:
            rich.print(
                f"🚀 [bold]'{package}'[/bold] updated from [red]{old_version}[/red] to [green]{new_version}[/green]"
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
    verbose = verbose or state.verbose

    if json:
        return _list_venvs_json()

    for name, metadata in list_packages():
        if short:
            _list_short(name, metadata)
        else:
            _list_normal(name, metadata, verbose=verbose)


@app.command("run")
def run(
    package: str,
    args: typing.Annotated[list[str], typer.Argument()] = None,  # type: ignore
    keep: bool = False,
    python: Annotated[str, typer.Option(help=OPTION_PYTHON_HELP_TEXT)] = "",
    no_cache: bool = False,
    binary: typing.Annotated[
        Optional[str],
        typer.Option(
            help="Custom name of an executable to run (e.g. 'semantic-release' in the package 'python-semantic-release')"
        ),
    ] = None,
):
    """Run a package in a temporary virtual environment."""
    output(run_package(package, args or [], keep=keep, python=python, no_cache=no_cache, binary_name=binary or ""))


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
    if state.verbose:
        rich.print("uvx", __version__, sys.argv[0])
        run_command(str(_uv), "--version", printfn=functools.partial(rich.print, end=" "))
        rich.print(str(_uv))
        rich.print("Python", sys.version.split(" ")[0], sys.executable)
    else:
        rich.print("uvx", __version__)
        run_command(str(_uv), "--version", printfn=rich.print)
        rich.print("Python", sys.version.split(" ")[0])


@app.callback(invoke_without_command=True, no_args_is_help=True)
def main(
    ctx: typer.Context,
    verbose: bool = False,
    # stops the program:
    version: bool = False,
) -> None:  # noqa
    """
    This callback will run before every command, setting the right global flags.

    Args:
        ctx: context to determine if a subcommand is passed, etc
        verbose: show more info in supported subcommands?
        version: display current version?

    """
    state.verbose = verbose

    if version:
        version_callback()
    elif not ctx.invoked_subcommand:
        rich.print("[yellow]Missing subcommand. Try `uvx --help` for more info.[/yellow]")
    # else: just continue


if __name__ == "__main__":  # pragma: no cover
    app()
