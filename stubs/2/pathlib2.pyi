import os
import sys

from typing import Any, AnyStr, IO, Iterable, Iterator, Optional, Text, Union

if sys.version_info >= (3, 6):
    _PurePathBase = os.PathLike[str]
else:
    _PurePathBase = object

class Path(_PurePathBase):
    anchor: str
    name: str
    parent: Path
    parents: Iterable[Path]
    parts: Iterable[Text]
    suffix: Text

    def __init__(self, path: AnyStr) -> None: ...

    @staticmethod
    def cwd() -> Path: ...

    def __div__(self: Path, child: Union[AnyStr, Path]) -> Path: ...
    def __truediv__(self: Path, child: Union[AnyStr, Path]) -> Path: ...

    def absolute(self) -> Path: ...
    def chmod(self, mode: int) -> None: ...
    def exists(self) -> bool: ...
    def glob(self, pattern: AnyStr) -> Iterator[Path]: ...
    def is_absolute(self) -> bool: ...
    def is_dir(self) -> bool: ...
    def is_file(self) -> bool: ...
    def is_symlink(self) -> bool: ...
    def iterdir(self) -> Iterator[Path]: ...
    def lstat(self) -> Any: ...
    def mkdir(self, mode: int = 511, parents: bool = False, exist_ok: bool = False) -> None: ...
    def open(self, mode: str = "r", encoding: str = "UTF-8") -> IO[Any]: ...
    def read_text(self, encoding: AnyStr) -> Text: ...
    def relative_to(self, pred: Path) -> Path: ...
    def rename(self, target: Path) -> None: ...
    def resolve(self) -> Path: ...
    def rglob(self, pattern: AnyStr) -> Iterator[Path]: ...
    def rmdir(self) -> None: ...
    def stat(self) -> Any: ...
    def symlink_to(self, target: AnyStr) -> None: ...
    def unlink(self) -> None: ...
    def with_name(self, name: AnyStr) -> Path: ...
    def with_suffix(self, ext: AnyStr) -> Path: ...
    def write_text(self, data: AnyStr, encoding: Optional[AnyStr] = None) -> None: ...
    def write_bytes(self, data: bytes) -> None: ...
