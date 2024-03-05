"""This file contains Logic related to the .metadata file."""
import json
import sys
import tempfile
import typing
from pathlib import Path
from typing import Optional

import plumbum
import msgspec
import threadful
from packaging.requirements import Requirement, InvalidRequirement

from ._python import _run_python_in_venv
from ._symlinks import check_symlinks

if typing.TYPE_CHECKING:
    from typing_extensions import Self


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

    def _convert_type(self, value: typing.Any) -> typing.Any:
        """Make the value JSON-encodable."""
        if isinstance(value, set):
            return list(value)
        return value

    def to_dict(self):
        """Convert the struct to a JSON-safe dictionary."""
        return {f: self._convert_type(getattr(self, f)) for f in self.__struct_fields__}

    def check_script_symlinks(self, name: str) -> "Self":
        """Update self.scripts with the current status of these scripts' symlinks."""
        self.scripts = check_symlinks(self.scripts.keys(), venv=name)
        return self


encoder = msgspec.msgpack.Encoder()
decoder = msgspec.msgpack.Decoder(type=Metadata)


def fake_install(spec: str) -> dict:
    _python = plumbum.local[sys.executable]

    _python("-m", "uv", "pip", "install", "pip")  # ensure we have pip

    with tempfile.NamedTemporaryFile() as f:
        _python("-m", "pip", "install", "--no-deps", "--dry-run", "--ignore-installed", "--report",
                f.name, spec)

        return json.load(f)


@threadful.thread
def resolve_local(spec: str) -> tuple[str | None, str | None]:
    try:
        full_data = fake_install(spec)
        install_data = full_data["install"][0]

        name = install_data['metadata']["name"]
        extras = install_data.get('requested_extras')
        file_url = install_data["download_info"]["url"]

        if extras:
            _extras = ",".join(extras)
            return f"{name}[{_extras}]", file_url
        else:
            return name, file_url
    except Exception:
        return None, None


def collect_metadata(spec: str) -> Metadata:
    """Parse an install spec into a (incomplete) Metadata object."""
    try:
        parsed_spec = Requirement(spec)

    except InvalidRequirement as e:
        local, path = threadful.animate(resolve_local(spec), text=f"Trying to install local package '{spec}'")

        if not local or not path:
            raise e

        parsed_spec = Requirement(local)

        spec = f"{parsed_spec.name} @ {path.removeprefix('file://')}"

    return Metadata(
        install_spec=spec,
        name=parsed_spec.name,
        scripts={},  # postponed
        extras=parsed_spec.extras,
        requested_version=str(parsed_spec.specifier),
        installed_version="",  # postponed
        python="",  # postponed
    )


def store_metadata(meta: Metadata, venv: Path):
    """Save the metadata struct to .metadata in a venv."""
    with (venv / ".metadata").open("wb") as f:
        f.write(encoder.encode(meta))


def read_metadata(venv: Path) -> Metadata | None:
    """Read the .metadata file for a venv."""
    metafile = venv / ".metadata"
    if not metafile.exists():
        return None

    with metafile.open("rb") as f:
        return typing.cast(Metadata, decoder.decode(f.read()))
