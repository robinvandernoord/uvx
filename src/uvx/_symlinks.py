import typing

from ._constants import BIN_DIR, WORK_DIR


def check_symlink(symlink: str, venv: str) -> bool:
    symlink_path = BIN_DIR / symlink
    target_path = WORK_DIR / "venvs" / venv

    return symlink_path.is_symlink() and target_path in symlink_path.resolve().parents


def check_symlinks(symlinks: typing.Iterable[str], venv: str) -> dict[str, bool]:
    return {k: check_symlink(k, venv) for k in symlinks}
