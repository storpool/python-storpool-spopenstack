#
# Copyright (c) 2019  StorPool.
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
""" Utility functions for storpool.spopenstack unit tests. """

import sys

if sys.version_info[0] >= 3:
    from importlib import machinery
else:
    import imp

from . import utils  # noqa: E402 pylint: disable=wrong-import-position


def _find_mock_file(module, path):
    """ Locate the unit_tests.mock_storpool modules. """
    if module in ("storpool.spapi", "storpool.spconfig"):
        if not path:
            return None
        name = module.split(".")[-1]
        spdir = utils.pathlib.Path(path[0])
        if spdir.name != "storpool":
            return None
        mock_path = spdir.parent / "unit_tests" / "mock_storpool"
        if not mock_path.is_dir():
            return None
        mock_file = (mock_path / name).with_suffix(".py")
        if not mock_file.is_file():
            return None
        return name, mock_file

    return None


class SPTestModuleFinder(object):
    """ Mimic the storpool namespace layout for the unit tests. """

    def __init__(self, name, mock_file):
        """ Initialize a loader. """
        self.name = name
        self.mock_file = mock_file

    def load_module(self, name):
        """ Load the located stub modules. """
        mock_path = self.mock_file.parent
        module_info = imp.find_module(self.name, [str(mock_path)])
        module = imp.load_module(name, *module_info)
        return module

    @classmethod
    def find_module(cls, module, path=None):
        """ Locate a (possibly mock) module to load for Python 2. """
        data = _find_mock_file(module, path)
        if data is None:
            return None

        name, mock_file = data
        return cls(name, mock_file)

    @classmethod
    def find_spec(cls, module, path=None, _target=None):
        """ Locate a (possibly mock) module to load for Python 2. """
        data = _find_mock_file(module, path)
        if data is None:
            return None

        _, mock_file = data
        return machinery.ModuleSpec(
            module, machinery.SourceFileLoader(module, str(mock_file))
        )
