"""This file contains Logic related to the .metadata file."""

import json
import tempfile
import typing
from pathlib import Path
from typing import Optional

import msgspec
import threadful
from packaging.requirements import InvalidRequirement, Requirement
from result import Err, Ok, Result

from ._maybe import Empty, Maybe
from ._python import _pip, _uv
from ._symlinks import check_symlinks

if typing.TYPE_CHECKING:
    from typing_extensions import Self

T = typing.TypeVar("T", bound=typing.Any)
V = typing.TypeVar("V", bound=typing.Any)


class Metadata(msgspec.Struct, array_like=True):
    """Structure of the .metadata file."""

    name: str
    scripts: dict[str, bool]  # {script: is_installed}
    install_spec: str  # e.g. '2fas' or '2fas[gui]>=0.1.0'
    extras: set[str]  # .e.g. {'gui'}
    requested_version: Optional[str]  # e.g. ">=0.1.0"
    installed_version: str
    python: str = ""
    python_raw: str = ""
    injected: Optional[set[str]] = None

    @typing.overload
    def _convert_type(self, value: set[V]) -> list[V]:  # type: ignore
        """Convert set of V to list of V."""

    @typing.overload
    def _convert_type(self, value: T) -> T:
        """Other types are not affected."""

    def _convert_type(self, value: set[V] | T) -> list[V] | T:
        """Make the value JSON-encodable."""
        if isinstance(value, set):
            return list(value)
        return value

    def to_dict(self) -> dict[str, typing.Any]:
        """Convert the struct to a JSON-safe dictionary."""
        return {f: self._convert_type(getattr(self, f)) for f in self.__struct_fields__}

    def check_script_symlinks(self, name: str) -> "Self":
        """Update self.scripts with the current status of these scripts' symlinks."""
        self.scripts = check_symlinks(self.scripts.keys(), venv=name)
        return self


encoder = msgspec.msgpack.Encoder()
decoder = msgspec.msgpack.Decoder(type=Metadata)


def fake_install(spec: str) -> dict:
    """Dry run pip to extract metadata of a local package."""
    _uv("pip", "install", "pip")  # ensure we have pip

    with tempfile.NamedTemporaryFile() as f:
        _pip("install", "--no-deps", "--dry-run", "--ignore-installed", "--report", f.name, spec)

        return json.load(f)


@threadful.thread
def resolve_local(spec: str) -> tuple[Maybe[str], Maybe[str]]:
    """Resolve the package name of a local package by dry run installing it."""
    try:
        full_data = fake_install(spec)
        install_data = full_data["install"][0]

        name = install_data["metadata"]["name"]
        extras = install_data.get("requested_extras")
        file_url = install_data["download_info"]["url"]

        if extras:
            _extras = ",".join(extras)
            return Ok(f"{name}[{_extras}]"), Ok(file_url)
        else:
            return Ok(name), Ok(file_url)
    except Exception:
        return Empty(), Empty()


def collect_metadata(spec: str) -> Result[Metadata, InvalidRequirement]:
    """Parse an install spec into a (incomplete) Metadata object."""
    try:
        parsed_spec = Requirement(spec)

    except InvalidRequirement as e:
        local, path = threadful.animate(resolve_local(spec), text=f"Trying to install local package '{spec}'")

        match local, path:
            case Ok(_local), Ok(_path):
                # both ok:
                parsed_spec = Requirement(_local)
                spec = f"{parsed_spec.name} @ {_path.removeprefix('file://')}"
            case _, _:
                # any err:
                return Err(e)

    return Ok(
        Metadata(
            install_spec=spec,
            name=parsed_spec.name,
            scripts={},  # postponed
            extras=parsed_spec.extras,
            requested_version=str(parsed_spec.specifier),
            installed_version="",  # postponed
            python="",  # postponed
        )
    )


def store_metadata(meta: Metadata, venv: Path):
    """Save the metadata struct to .metadata in a venv."""
    with (venv / ".metadata").open("wb") as f:
        f.write(encoder.encode(meta))


def read_metadata(venv: Path) -> Maybe[Metadata]:
    """Read the .metadata file for a venv."""
    metafile = venv / ".metadata"
    if not metafile.exists():
        return Empty()

    with metafile.open("rb") as f:
        data = decoder.decode(f.read())  # type: Metadata
        return Ok(data)
