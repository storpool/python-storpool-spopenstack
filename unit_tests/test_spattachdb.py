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
""" Test the classes in the storpool.spopenstack.spattachdb module. """

from __future__ import print_function

import json as jsonmod
import sys

try:
    from typing import Any, Callable, Dict, List, Optional, Tuple, Union

    CallArgsTupleFull = Tuple[str, List[Any], Dict[str, Any]]
    CallArgsTupleShort = Tuple[List[Any], Dict[str, Any]]

    CallArgsTuple = Union[CallArgsTupleShort, CallArgsTupleFull]
except ImportError:
    pass

import pytest
import six

from . import sp_test_import
from . import utils

sys.meta_path.insert(0, sp_test_import.SPTestModuleFinder)  # type: ignore

# pylint: disable=wrong-import-position,wrong-import-order
if sys.version_info[0] < 3:
    import mock  # pylint: disable=import-error
else:
    from unittest import mock

from storpool import spapi  # noqa: E402 pylint: disable=no-name-in-module
from storpool import spconfig  # noqa: E402 pylint: disable=no-name-in-module

from storpool.spopenstack import spattachdb  # noqa: E402


def with_attachdb(
    func,  # type: Callable[[utils.pathlib.Path, spattachdb.AttachDB], None]
):  # type: (...) -> Callable[[], None]
    """ Prepare the environment for an AttachDB test. """

    @utils.with_tempdir
    def wrapped(tempd):
        # type: (utils.pathlib.Path) -> None
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
    # type: (utils.pathlib.Path, spattachdb.AttachDB) -> None
    """ Test some trivial behavior of the AttachDB class. """
    cfg = att.config()
    assert isinstance(cfg, spconfig.SPConfig)
    cfg_second = att.config()
    assert cfg_second is cfg

    api = att.api()
    assert api.port == 81
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
        assert napi.port == 8000

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
    # type: (utils.pathlib.Path, spattachdb.AttachDB) -> None
    # pylint: disable=protected-access
    """ Test the "wait for the volume to be attached" method. """
    volname = att.volumeName("beef")
    spname = "/dev/storpool/" + volname
    state = {"count": 0}

    def mock_exists(path):
        # type: (str) -> bool
        """ Make sure os.path.exists() is called for the right volume. """
        assert path == spname
        state["count"] += 1
        return False

    def mock_sleep(interval):
        # type: (int) -> None
        """ No need to waste time sleeping. """
        assert interval > 0
        assert interval < 10

    with mock.patch("os.path.exists", new=mock_exists):
        with mock.patch("time.sleep", new=mock_sleep):
            att._attach_and_wait(42, volname, False, 2)

    assert state["count"] == 10
    assert att.api().reassign == [[{"volume": volname, "rw": [42]}]]

    with pytest.raises(spapi.ApiError):
        att._attach_and_wait(42, volname, True, 2)

    with mock.patch("os.path.exists", new=mock_exists):
        with mock.patch("time.sleep", new=mock_sleep):
            att._attach_and_wait(43, volname, True, 1)

    assert state["count"] == 20
    assert att.api().reassign == [
        [{"volume": volname, "rw": [42]}],
        [{"snapshot": volname, "ro": [43]}],
    ]


@with_attachdb
def test_detach_and_wait(_tempf, att):
    # type: (utils.pathlib.Path, spattachdb.AttachDB) -> None
    # pylint: disable=protected-access
    """ Test the "wait for a volume to go away" method. """
    client = 42
    volname = att.volumeName("beef")
    state = {"count": 0}
    expected = {"volume": volname, "detach": [client], "force": False}

    def mock_reassign(json):
        # type: (List[spapi.AttachmentDescDict]) -> None
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
        # type: (int) -> None
        """ No need to waste time sleeping. """
        assert interval > 0
        assert interval < 10

    with mock.patch("time.sleep", new=mock_sleep):
        att.api().volumesReassign = mock_reassign  # type: ignore
        att._detach_and_wait(client, volname, False)
        assert state["count"] == 11

        state = {"count": 0}
        expected = {"snapshot": volname, "detach": [client], "force": False}
        att._detach_and_wait(client, volname, True)
        assert state["count"] == 11


def compare_attach(item):
    # type: (CallArgsTuple) -> Tuple[Any, Any, Any, Any]
    """Tweak the arguments of a SPAttachDB._attach_and_wait() call."""
    if len(item) == 2:
        args, kwargs = item  # type: ignore
    else:
        args, kwargs = item[1], item[2]  # type: ignore
    assert (args, item) == ((), item)

    return (
        kwargs["client"],
        kwargs["volume"],
        kwargs["volsnap"],
        kwargs["rights"],
    )


def compare_detach(item):
    # type: (CallArgsTuple) -> Tuple[Any, Any, Any]
    """Tweak the arguments of a SPAttachDB._detach_and_wait() call."""
    if len(item) == 2:
        args, kwargs = item  # type: ignore
    else:
        args, kwargs = item[1], item[2]  # type: ignore
    assert (args, item) == ((), item)

    return (
        kwargs["client"],
        kwargs["volume"],
        kwargs["volsnap"],
    )


@with_attachdb
def test_sync(tempf, att):
    # type: (utils.pathlib.Path, spattachdb.AttachDB) -> None
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

    def run_sync(  # pylint: disable=too-many-arguments
        args,  # type: Tuple[str, Optional[str]]
        expected,  # type: Tuple[List[mock.call], List[mock.call]]
        volumes=None,  # type: Optional[List[spapi.VolumeSummary]]
        snapshots=None,  # type: Optional[List[spapi.SnapshotSummary]]
        attachments=None,  # type: Optional[List[spapi.AttachmentDesc]]
        expected_json=None,  # type: Optional[Any]
    ):  # type: (...) -> None
        """Run att.sync() in the specified environment."""

        with mock.patch.object(att, "_attach_and_wait") as att_wait:
            with mock.patch.object(att, "_detach_and_wait") as det_wait:
                att.api().volumes = volumes if volumes else []
                att.api().snapshots = snapshots if snapshots else []
                att.api().attachments = attachments if attachments else []
                att.sync(args[0], args[1])
                assert sorted(
                    att_wait.call_args_list, key=compare_attach
                ) == sorted(expected[0], key=compare_attach)
                assert sorted(
                    det_wait.call_args_list, key=compare_detach
                ) == sorted(expected[1], key=compare_detach)

        if expected_json is None:
            assert jsonmod.loads(tempf.read_text(encoding="UTF-8")) == voldata
        else:
            assert (
                jsonmod.loads(tempf.read_text(encoding="UTF-8"))
                == expected_json
            )

            tempf.write_text(contents, encoding="UTF-8")
            assert jsonmod.loads(tempf.read_text(encoding="UTF-8")) == voldata

    run_sync(
        ("a", None),
        (
            [mock.call(client=42, volume="os-vol-a", volsnap=False, rights=2)],
            [],
        ),
        volumes=[spapi.VolumeSummary("os-vol-a")],
        expected_json={
            "a": {
                "id": "a",
                "volume": "os-vol-a",
                "volsnap": False,
                "rights": 2,
            },
        },
    )

    run_sync(
        ("a", None),
        ([], []),
        volumes=[
            spapi.VolumeSummary("os-vol-a"),
            spapi.VolumeSummary("ignore"),
        ],
        snapshots=[spapi.SnapshotSummary("os-snap-b")],
        attachments=[
            spapi.AttachmentDesc(
                volume="os-vol-a", client=42, snapshot=False, rights="rw"
            ),
            spapi.AttachmentDesc(
                volume="os-snap-b", client=42, snapshot=True, rights="ro"
            ),
        ],
    )

    run_sync(
        ("a", None),
        (
            [
                mock.call(
                    client=42, volume="os-vol-a", volsnap=False, rights=2
                ),
                mock.call(
                    client=42, volume="os-snap-b", volsnap=True, rights=1
                ),
            ],
            [],
        ),
        volumes=[
            spapi.VolumeSummary("os-vol-a"),
            spapi.VolumeSummary("ignore"),
        ],
        snapshots=[spapi.SnapshotSummary("os-snap-b")],
    )

    assert jsonmod.loads(tempf.read_text(encoding="UTF-8")) == voldata

    run_sync(
        ("a", None),
        (
            [mock.call(client=42, volume="os-vol-a", volsnap=False, rights=2)],
            [],
        ),
        volumes=[
            spapi.VolumeSummary("os-vol-a"),
            spapi.VolumeSummary("os-vol-extra"),
        ],
        snapshots=[
            spapi.SnapshotSummary("os-snap-b"),
            spapi.SnapshotSummary("os-snap-extra"),
        ],
        attachments=[
            spapi.AttachmentDesc(
                volume="os-vol-a", client=41, snapshot=False, rights="rw"
            ),
            spapi.AttachmentDesc(
                volume="os-vol-extra", client=42, snapshot=False, rights="rw",
            ),
            spapi.AttachmentDesc(
                volume="os-snap-b", client=42, snapshot=True, rights="ro"
            ),
            spapi.AttachmentDesc(
                volume="os-snap-extra", client=42, snapshot=True, rights="ro"
            ),
        ],
    )

    run_sync(
        ("a", "os-vol-detached"),
        (
            [mock.call(client=42, volume="os-vol-a", volsnap=False, rights=2)],
            [mock.call(client=42, volume="os-vol-detached", volsnap=False)],
        ),
        volumes=[
            spapi.VolumeSummary("os-vol-a"),
            spapi.VolumeSummary("os-vol-detached"),
            spapi.VolumeSummary("os-vol-extra"),
        ],
        snapshots=[
            spapi.SnapshotSummary("os-snap-b"),
            spapi.SnapshotSummary("os-snap-extra"),
        ],
        attachments=[
            spapi.AttachmentDesc(
                volume="os-vol-a", client=41, snapshot=False, rights="rw"
            ),
            spapi.AttachmentDesc(
                volume="os-vol-detached",
                client=42,
                snapshot=False,
                rights="rw",
            ),
            spapi.AttachmentDesc(
                volume="os-vol-extra", client=42, snapshot=False, rights="rw",
            ),
            spapi.AttachmentDesc(
                volume="os-snap-b", client=42, snapshot=True, rights="ro"
            ),
            spapi.AttachmentDesc(
                volume="os-snap-extra", client=42, snapshot=True, rights="ro"
            ),
        ],
    )

    run_sync(
        ("a", "os-snap-detached"),
        (
            [mock.call(client=42, volume="os-vol-a", volsnap=False, rights=2)],
            [mock.call(client=42, volume="os-snap-detached", volsnap=True)],
        ),
        volumes=[
            spapi.VolumeSummary("os-vol-a"),
            spapi.VolumeSummary("os-vol-extra"),
        ],
        snapshots=[
            spapi.SnapshotSummary("os-snap-b"),
            spapi.SnapshotSummary("os-snap-detached"),
            spapi.SnapshotSummary("os-snap-extra"),
        ],
        attachments=[
            spapi.AttachmentDesc(
                volume="os-vol-a", client=41, snapshot=False, rights="rw"
            ),
            spapi.AttachmentDesc(
                volume="os-vol-extra", client=42, snapshot=False, rights="rw",
            ),
            spapi.AttachmentDesc(
                volume="os-snap-b", client=42, snapshot=True, rights="ro"
            ),
            spapi.AttachmentDesc(
                volume="os-snap-detached",
                client=42,
                snapshot=True,
                rights="ro",
            ),
            spapi.AttachmentDesc(
                volume="os-snap-extra", client=42, snapshot=True, rights="ro"
            ),
        ],
    )
