"""This file contains Logic related to the .metadata file."""
import sys
import typing
from pathlib import Path
from typing import Optional

import plumbum
import quickle  # type: ignore
import threadful
from packaging.requirements import Requirement, InvalidRequirement

from ._python import _run_python_in_venv
from ._symlinks import check_symlinks

if typing.TYPE_CHECKING:
    from typing_extensions import Self


class Metadata(quickle.Struct):
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


quickle_enc = quickle.Encoder(registry=[Metadata])
quickle_dec = quickle.Decoder(registry=[Metadata])


@threadful.thread
def resolve_local(spec: str):
    # todo: finish
    _python = plumbum.local[sys.executable]

    _python("-m", "uv", "pip", "install", "pip")  # ensure we have pip

    result = _python("-m", "pip", "install", "--no-deps", "--dry-run", "--ignore-installed", "--report",
                     "/tmp/out.json", spec)

    print(result)
    return result


def collect_metadata(spec: str) -> Metadata:
    """Parse an install spec into a (incomplete) Metadata object."""
    try:
        parsed_spec = Requirement(spec)

        return Metadata(
            install_spec=spec,
            name=parsed_spec.name,
            scripts={},  # postponed
            extras=parsed_spec.extras,
            requested_version=str(parsed_spec.specifier),
            installed_version="",  # postponed
            python="",  # postponed
        )
    except InvalidRequirement:
        threadful.animate(resolve_local(spec), text=f"Trying to install local package '{spec}'")
        print("reeeeeeeeeeeeeeee")
        exit(1)


def store_metadata(meta: Metadata, venv: Path):
    """Save the metadata struct to .metadata in a venv."""
    with (venv / ".metadata").open("wb") as f:
        f.write(quickle_enc.dumps(meta))


def read_metadata(venv: Path) -> Metadata | None:
    """Read the .metadata file for a venv."""
    metafile = venv / ".metadata"
    if not metafile.exists():
        return None

    with metafile.open("rb") as f:
        return typing.cast(Metadata, quickle_dec.loads(f.read()))
