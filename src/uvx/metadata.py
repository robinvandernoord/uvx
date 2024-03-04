import typing
from pathlib import Path
from typing import Optional

import quickle
from packaging.requirements import Requirement

from ._symlinks import check_symlinks


class Metadata(quickle.Struct):
    name: str
    scripts: dict[str, bool]  # {script: is_installed}
    install_spec: str  # e.g. '2fas' or '2fas[gui]>=0.1.0'
    extras: set[str]  # .e.g. {'gui'}
    requested_version: Optional[str]  # e.g. ">=0.1.0"
    installed_version: str
    python: str = ""
    python_raw: str = ""

    def _convert_type(self, value):
        if isinstance(value, set):
            return list(value)
        return value

    def to_dict(self):
        return {f: self._convert_type(getattr(self, f)) for f in self.__struct_fields__}

    def check_script_symlinks(self, name: str):
        self.scripts = check_symlinks(self.scripts.keys(), venv=name)
        return self


quickle_enc = quickle.Encoder(registry=[Metadata])
quickle_dec = quickle.Decoder(registry=[Metadata])


def collect_metadata(spec: str) -> Metadata:
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


def store_metadata(meta: Metadata, venv: Path):
    with (venv / ".metadata").open("wb") as f:
        f.write(quickle_enc.dumps(meta))


def read_metadata(venv: Path) -> Metadata | None:
    metafile = venv / ".metadata"
    if not metafile.exists():
        return None

    with metafile.open("rb") as f:
        return typing.cast(Metadata, quickle_dec.loads(f.read()))


def get_metadata(): ...
