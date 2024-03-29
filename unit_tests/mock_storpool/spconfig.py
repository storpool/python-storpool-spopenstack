#
# Copyright (c) 2019 - 2021  StorPool.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
""" Mock the storpool.spconfig.SPConfig class for testing """

try:
    from typing import Dict, Iterator, Optional, Tuple
except ImportError:
    pass


def get_config_dictionary():
    # type: () -> Dict[str, str]
    """Return the dictionary to be used for configuration."""
    return {
        "SP_OURID": "42",
        "SP_API_HTTP_HOST": "localhost",
        "SP_API_HTTP_PORT": "81",
        "SP_AUTH_TOKEN": "1122334455667788",
    }


# pylint: disable=too-few-public-methods
class SPConfig(object):
    """Mock the SPConfig class."""

    def __init__(self, override_config=None):
        # type: (SPConfig, Optional[Dict[str, str]]) -> None
        if override_config is None:
            self._dict = get_config_dictionary()
        else:
            self._dict = override_config

    def __getitem__(self, key):
        # type: (SPConfig, str) -> str
        """Return a configuration value."""
        return self._dict[key]

    def get(self, key, default=None):
        # type: (SPConfig, str, Optional[str]) -> Optional[str]
        """Return a configuration value with a fallback."""
        return self._dict.get(key, default)

    def items(self):
        # type: (SPConfig) -> Iterator[Tuple[str, str]]
        """Return an iterator over the configuration values."""
        # Forget about Python 2.x's non-iterator implementation.
        return iter(self._dict.items())
