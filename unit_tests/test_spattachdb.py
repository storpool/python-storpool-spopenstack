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
""" Test the classes in the storpool.spopenstack.spattachdb module. """

from __future__ import print_function

import json as jsonmod
import sys

import mock
import pytest
import six

from . import sp_test_import
from . import utils

sys.meta_path.insert(0, sp_test_import.SPTestModuleFinder)

# pylint: disable=wrong-import-position,wrong-import-order
from storpool import spapi  # noqa: E402 pylint: disable=no-name-in-module
from storpool import spconfig  # noqa: E402 pylint: disable=no-name-in-module

from storpool.spopenstack import spattachdb  # noqa: E0402


def with_attachdb(func):
    """ Prepare the environment for an AttachDB test. """

    @utils.with_tempdir
    def wrapped(tempd):
        """ Create a couple of objects, invoke the function. """
        tempf = tempd / "attach.json"
        tempf.write_text(u"{}", encoding="UTF-8")

        log = mock.Mock(spec=["warn"])
        log.warn = mock.Mock(spec=["__call__"])
        att = spattachdb.AttachDB(fname=str(tempf), log=log)

        func(tempf, att)

    return wrapped


@with_attachdb
def test_trivial(tempf, att):
    """ Test some trivial behavior of the AttachDB class. """
    cfg = att.config()
    assert isinstance(cfg, spconfig.SPConfig)
    cfg_second = att.config()
    assert cfg_second is cfg

    api = att.api()
    assert api.port == "81"
    api_second = att.api()
    assert api_second is api

    assert att.volumePrefix() == "os"
    assert att.volumeName("feed") == "os--volume-feed"
    assert att.volsnapName("beefed", "616") == "os--volsnap-beefed--req-616"
    assert (
        att.snapshotName("image", "c0ffee")
        == "os--image--none--snapshot-c0ffee"
    )
    assert (
        att.snapshotName("image", "c0ffee", "purpose")
        == "os--image--purpose--snapshot-c0ffee"
    )

    cfg_dict = spconfig.get_config_dictionary()
    cfg_dict["SP_OURID"] = "1"
    cfg_dict["SP_OPENSTACK_VOLUME_PREFIX"] = "lab"
    cfg_dict["SP_API_HTTP_PORT"] = "8000"
    with mock.patch(
        "storpool.spconfig.get_config_dictionary", new=lambda: cfg_dict
    ):
        natt = spattachdb.AttachDB(fname=str(tempf), log=att.LOG)
        napi = natt.api()
        assert napi.port == "8000"

        assert natt.volumePrefix() == "lab"
        assert natt.volumeName("feed") == "lab--volume-feed"
        assert (
            natt.volsnapName("beefed", "616") == "lab--volsnap-beefed--req-616"
        )
        assert (
            natt.snapshotName("image", "c0ffee")
            == "lab--image--none--snapshot-c0ffee"
        )
        assert (
            natt.snapshotName("image", "c0ffee", "purpose")
            == "lab--image--purpose--snapshot-c0ffee"
        )


@with_attachdb
def test_attach_and_wait(_tempf, att):
    # pylint: disable=protected-access
    """ Test the "wait for the volume to be attached" method. """
    volname = att.volumeName("beef")
    spname = "/dev/storpool/" + volname
    state = {"count": 0}

    def mock_exists(path):
        """ Make sure os.path.exists() is called for the right volume. """
        assert path == spname
        state["count"] += 1
        return False

    def mock_sleep(interval):
        """ No need to waste time sleeping. """
        assert interval > 0
        assert interval < 10

    with mock.patch("os.path.exists", new=mock_exists):
        with mock.patch("time.sleep", new=mock_sleep):
            att._attach_and_wait("42", volname, False, 2)

    assert state["count"] == 10
    assert att.api().reassign == [[{"volume": volname, "rw": ["42"]}]]

    with pytest.raises(spapi.ApiError):
        att._attach_and_wait("42", volname, True, 2)

    with mock.patch("os.path.exists", new=mock_exists):
        with mock.patch("time.sleep", new=mock_sleep):
            att._attach_and_wait("43", volname, True, 1)

    assert state["count"] == 20
    assert att.api().reassign == [
        [{"volume": volname, "rw": ["42"]}],
        [{"snapshot": volname, "ro": ["43"]}],
    ]


@with_attachdb
def test_detach_and_wait(_tempf, att):
    # pylint: disable=protected-access
    """ Test the "wait for a volume to go away" method. """
    client = "42"
    volname = att.volumeName("beef")
    state = {"count": 0}
    expected = {"volume": volname, "detach": [client], "force": False}

    def mock_reassign(json):
        """ Mock a volumesReassign() invocation. """
        assert state["count"] < 11
        expected["force"] = state["count"] == 10
        assert (state["count"], json) == (state["count"], [expected])
        state["count"] += 1
        if state["count"] <= 10:
            raise spapi.ApiError(
                "oof",
                {
                    "error": {
                        "name": "invalidParam",
                        "descr": "volume is open at a client",
                    }
                },
            )

    def mock_sleep(interval):
        """ No need to waste time sleeping. """
        assert interval > 0
        assert interval < 10

    with mock.patch("time.sleep", new=mock_sleep):
        att.api().volumesReassign = mock_reassign
        att._detach_and_wait(client, volname, False)
        assert state["count"] == 11

        state = {"count": 0}
        expected = {"snapshot": volname, "detach": [client], "force": False}
        att._detach_and_wait(client, volname, True)
        assert state["count"] == 11


@with_attachdb
def test_sync(tempf, att):
    """ Test the main purpose of AttachDB: the sync() method. """

    voldata = {
        "a": {"id": "a", "volume": "os-vol-a", "volsnap": False, "rights": 2},
        "b": {"id": "b", "volume": "os-snap-b", "volsnap": True, "rights": 1},
    }
    contents = six.text_type(jsonmod.dumps(voldata))
    tempf.write_text(contents, encoding="UTF-8")

    # OK, so this needs to be fixed in AttachDB...
    att.config()

    with pytest.raises(Exception):
        att.sync("no", None)
    assert tempf.read_text(encoding="UTF-8") == contents

    att.sync("no", "no")
    assert tempf.read_text(encoding="UTF-8") == contents

    with mock.patch.object(att, "_attach_and_wait") as att_wait:
        with mock.patch.object(att, "_detach_and_wait") as det_wait:
            att.api().volumes = [spapi.Volume("os-vol-a")]
            att.sync("a", None)
            assert att_wait.call_count == 1
            assert det_wait.call_count == 0

    assert jsonmod.loads(tempf.read_text(encoding="UTF-8")) == {
        "a": {"id": "a", "volume": "os-vol-a", "volsnap": False, "rights": 2}
    }
    tempf.write_text(contents, encoding="UTF-8")
    assert jsonmod.loads(tempf.read_text(encoding="UTF-8")) == voldata

    with mock.patch.object(att, "_attach_and_wait") as att_wait:
        with mock.patch.object(att, "_detach_and_wait") as det_wait:
            att.api().volumes = [
                spapi.Volume("os-vol-a"),
                spapi.Volume("ignore"),
            ]
            att.api().snapshots = [spapi.Snapshot("os-snap-b")]
            att.sync("a", None)
            assert att_wait.call_count == 2
            assert det_wait.call_count == 0

    assert jsonmod.loads(tempf.read_text(encoding="UTF-8")) == voldata

    with mock.patch.object(att, "_attach_and_wait") as att_wait:
        with mock.patch.object(att, "_detach_and_wait") as det_wait:
            att.api().volumes = [
                spapi.Volume("os-vol-a"),
                spapi.Volume("ignore"),
            ]
            att.api().snapshots = [spapi.Snapshot("os-snap-b")]
            att.api().attachments = [
                spapi.Attachment(
                    volume="os-vol-a", client=42, snapshot=False, rights="rw"
                ),
                spapi.Attachment(
                    volume="os-snap-b", client=42, snapshot=True, rights="ro"
                ),
            ]
            att.sync("a", None)
            assert att_wait.call_count == 0
            assert det_wait.call_count == 0

    assert jsonmod.loads(tempf.read_text(encoding="UTF-8")) == voldata

    with mock.patch.object(att, "_attach_and_wait") as att_wait:
        with mock.patch.object(att, "_detach_and_wait") as det_wait:
            att.api().volumes = [
                spapi.Volume("os-vol-a"),
                spapi.Volume("os-vol-detach"),
            ]
            att.api().snapshots = [spapi.Snapshot("os-snap-b")]
            att.api().attachments = [
                spapi.Attachment(
                    volume="os-vol-a", client=41, snapshot=False, rights="rw"
                ),
                spapi.Attachment(
                    volume="os-vol-detach",
                    client=42,
                    snapshot=False,
                    rights="rw",
                ),
                spapi.Attachment(
                    volume="os-snap-b", client=42, snapshot=True, rights="ro"
                ),
            ]
            att.sync("a", None)
            assert att_wait.call_count == 1
            assert det_wait.call_count == 1

    assert jsonmod.loads(tempf.read_text(encoding="UTF-8")) == voldata
