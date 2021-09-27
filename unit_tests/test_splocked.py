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
"""Test the classes in the storpool.spopenstack.splocked module."""

import errno
import json
import sys

try:
    from typing import Text
except ImportError:
    pass

import pytest

from . import utils
from .mock_storpool import spapi, spconfig

sys.modules["storpool.spapi"] = spapi
sys.modules["storpool.spconfig"] = spconfig

# pylint: disable=wrong-import-position,wrong-import-order
if sys.version_info[0] < 3:
    import mock  # pylint: disable=import-error
else:
    from unittest import mock

from storpool.spopenstack import splocked  # noqa: E402


@utils.with_tempdir
def test_lockfile(tempd):
    # type: (utils.pathlib.Path) -> None
    """Test that an SPLockedFile object behaves sensibly."""
    assert tempd.is_dir()

    tempf = tempd / "testfile.json"
    fname = str(tempf.absolute())

    assert not tempf.exists()
    contents = u"stuff\n"
    tempf.write_text(contents, encoding="UTF-8")

    def mock_json_loads(loaded):
        # type: (str) -> int
        """Mock json.loads() on the temporary file."""
        assert tempf.is_file()
        assert tempf.stat().st_size != 0
        assert loaded == contents.encode("UTF-8")
        return 616

    def mock_json_dumps(dumped):
        # type: (int) -> Text
        """Mock json.dumps() on the temporary file."""
        assert tempf.is_file()
        assert tempf.stat().st_size == 0
        assert dumped == 617
        return u"more stuff\n"

    locked = splocked.SPLockedFile(fname)
    with locked:
        assert tempf.read_text(encoding="UTF-8") == contents

    assert tempf.read_text(encoding="UTF-8") == contents

    with mock.patch("json.loads", new=mock_json_loads):
        assert tempf.read_text(encoding="UTF-8") == contents
        assert locked.jsload() == 616

    assert tempf.read_text(encoding="UTF-8") == contents

    tempf.write_text(u"", encoding="UTF-8")
    with mock.patch("json.dumps", new=mock_json_dumps):
        locked.jsdump(617)
    assert tempf.is_file()
    assert tempf.read_text(encoding="UTF-8") == "more stuff\n"


@utils.with_tempdir
def test_jsondb(tempd):
    # type: (utils.pathlib.Path) -> None
    """Test the SPLockedJSONDB class methods."""
    tempf = tempd / "db.json"

    assert tempd.is_dir()
    assert not tempf.exists()

    jdb = splocked.SPLockedJSONDB(str(tempf.absolute()))
    assert not tempf.exists()

    def assert_db():
        # type: () -> None
        """Make sure the database file exists and is not empty."""
        assert tempf.is_file()
        assert tempf.stat().st_size != 0
        assert json.loads(tempf.read_text(encoding="UTF-8")) == jdb.get()

    with pytest.raises((IOError, OSError)) as err:
        jdb.get()
    assert err.value.errno == errno.ENOENT
    assert not tempf.exists()

    tempf.write_text(u"{}", encoding="UTF-8")
    assert jdb.get() == {}

    jdb.add(u"a", u"value")
    assert_db()

    assert jdb.get() == {u"a": u"value"}
    assert_db()

    jdb.add(u"b", 42)
    jdb.add(u"c", u"nothing")
    assert jdb.get() == {u"a": u"value", u"b": 42, u"c": u"nothing"}
    assert_db()

    jdb.remove(u"b")
    assert jdb.get() == {u"a": u"value", u"c": u"nothing"}
    assert_db()

    jdb.remove_keys([u"c", u"d"])
    assert jdb.get() == {u"a": u"value"}
    assert_db()
