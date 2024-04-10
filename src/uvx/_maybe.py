import typing

from result import Err, Ok

T = typing.TypeVar("T")


class Empty(Err[None]):
    """
    Alias for Err[None], used by Maybe.

    Usage:
    Result[str, None] = Maybe[str]
    """

    def __init__(self) -> None:
        """Set up the Err result with None as it's value."""
        super().__init__(None)


Maybe = Ok[T] | Empty
