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
""" Test the classes in the storpool.spopenstack.splocked module. """

import json
import sys

try:
    from typing import Text
except ImportError:
    pass

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
    """ Test that an SPLockedFile object behaves sensibly. """
    tempf = tempd / "testfile.json"
    lockf = tempd / (tempf.name + ".splock")
    assert tempd.is_dir()
    assert not tempf.exists()
    assert not lockf.exists()

    fname = str(tempf.absolute())

    def mock_json_loads(loaded):
        # type: (str) -> int
        """ Mock json.loads() on the temporary file. """
        assert tempf.is_file()
        assert tempf.stat().st_size != 0
        assert lockf.is_file()
        assert loaded == "stuff\n"
        return 616

    def mock_json_dumps(dumped):
        # type: (int) -> Text
        """ Mock json.dumps() on the temporary file. """
        assert tempf.is_file()
        assert tempf.stat().st_size == 0
        assert lockf.is_file()
        assert dumped == 617
        return u"more stuff\n"

    locked = splocked.SPLockedFile(fname)
    with locked:
        assert not tempf.exists()
        assert lockf.is_file()

    assert not tempf.exists()
    assert not lockf.exists()

    tempf.write_text(u"stuff\n", encoding="UTF-8")
    assert tempf.is_file()
    assert tempf.stat().st_size != 0
    with mock.patch("json.loads", new=mock_json_loads):
        assert locked.jsload() == 616

    assert tempf.is_file()
    assert not lockf.exists()

    tempf.unlink()
    assert not tempf.exists()
    with mock.patch("json.dumps", new=mock_json_dumps):
        locked.jsdump(617)
    assert tempf.is_file()
    assert not lockf.exists()
    assert tempf.read_text(encoding="UTF-8") == "more stuff\n"


@utils.with_tempdir
def test_jsondb(tempd):
    # type: (utils.pathlib.Path) -> None
    """ Test the SPLockedJSONDB class methods. """
    tempf = tempd / "db.json"
    lockf = tempd / (tempf.name + ".splock")

    def assert_none():
        # type: () -> None
        """ Make sure none of the files exist. """
        assert not tempf.exists()
        assert not lockf.exists()

    assert tempd.is_dir()
    assert_none()

    jdb = splocked.SPLockedJSONDB(str(tempf.absolute()))
    assert_none()

    def assert_db():
        # type: () -> None
        """ Make sure the database file exists and is not empty. """
        assert tempf.is_file()
        assert tempf.stat().st_size != 0
        assert not lockf.exists()
        assert json.loads(tempf.read_text(encoding="UTF-8")) == jdb.get()

    assert jdb.get() == {}
    assert_none()

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
