#
# Copyright (c) 2019, 2020  StorPool.
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
    from typing import Dict, Optional
except ImportError:
    pass


def get_config_dictionary():
    # type: () -> Dict[str, str]
    """ Return the dictionary to be used for configuration. """
    return {
        "SP_OURID": "42",
        "SP_API_HTTP_HOST": "localhost",
        "SP_API_HTTP_PORT": "81",
        "SP_AUTH_TOKEN": "1122334455667788",
    }


# pylint: disable=too-few-public-methods
class SPConfig(object):
    """ Mock the SPConfig class. """

    def __init__(self):
        # type: (SPConfig) -> None
        self._dict = get_config_dictionary()

    def __getitem__(self, key):
        # type: (SPConfig, str) -> str
        """ Return a configuration value. """
        return self._dict[key]

    def get(self, key, default=None):
        # type: (SPConfig, str, Optional[str]) -> Optional[str]
        """ Return a configuration value with a fallback. """
        return self._dict.get(key, default)
