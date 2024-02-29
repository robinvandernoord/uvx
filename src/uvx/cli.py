"""This file builds the Typer cli."""

import typer

from .core import create_venv, install_package, uninstall_package

app = typer.Typer()


@app.command()
def install(package_name: str, force: bool = False):
    """Install a package (by pip name)."""
    venv = create_venv(package_name)
    install_package(package_name, venv, force=force)


@app.command(name="remove")
@app.command(name="uninstall")
def uninstall(package_name: str, force: bool = False):
    """Uninstall a package (by pip name)."""
    uninstall_package(package_name, force=force)


# list

# run

# upgrade

# self-upgrade (uv and uvx)

# ...
