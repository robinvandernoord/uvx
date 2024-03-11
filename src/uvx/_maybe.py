import typing

from result import Err, Ok

T = typing.TypeVar("T")


class Empty(Err[None]):
    def __init__(self) -> None:
        super().__init__(None)


Maybe = Ok[T] | Empty
