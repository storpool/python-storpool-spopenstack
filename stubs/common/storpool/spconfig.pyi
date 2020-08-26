from typing import Dict


def get_config_dictionary() -> Dict[str, str]: ...


class SPConfig(object):
    def __getitem__(self, key: str) -> str: ...

    def get(self, key: str, default: str) -> str: ...
