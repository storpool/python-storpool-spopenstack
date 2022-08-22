from typing import Dict, Iterator, Optional, Tuple


def get_config_dictionary() -> Dict[str, str]: ...


class SPConfig(object):
    def __init__(self, override_config: Optional[Dict[str, str]] = None) -> None: ...

    def __getitem__(self, key: str) -> str: ...

    def get(self, key: str, default: str) -> str: ...

    def items(self) -> Iterator[Tuple[str, str]]: ...
