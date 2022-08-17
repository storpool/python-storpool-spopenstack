#
# Copyright (c) 2019 - 2022  StorPool.
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
"""Utility functions for storpool.spopenstack unit tests."""

from __future__ import print_function

import subprocess
import sys
import tempfile

if sys.version_info[0] >= 3:
    import pathlib
else:
    import pathlib2 as pathlib  # type: ignore

try:
    from typing import Callable
except ImportError:
    pass


# Ah great, Python 2.x's tempfile does not have TemporaryDirectory
def with_tempdir(func):
    # type: (Callable[[pathlib.Path], None]) -> Callable[[], None]
    """Decorate a function, create a temporary directory."""

    def wrapper():
        # type: () -> None
        """Create a temporary directory, invoke the target function."""
        tempd = pathlib.Path(tempfile.mkdtemp())
        try:
            return func(tempd)
        finally:
            subprocess.call(["rm", "-rf", "--", str(tempd)])

    return wrapper


__all__ = ["pathlib", "with_tempdir"]
