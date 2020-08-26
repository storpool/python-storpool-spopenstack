#
# -
# Copyright (c) 2014, 2015, 2019, 2020  StorPool.
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

"""
Helper routines for the StorPool drivers in the OpenStack codebase.
"""

import collections
import os
import time

try:
    import logging

    from typing import Dict, List, Optional, Text, Tuple, TypedDict

    Attach = TypedDict(
        "Attach",
        {
            "volume": str,
            "type": str,
            "id": str,
            "rights": int,
            "volsnap": bool,
            "remove_on_detach": bool,
        },
    )
except ImportError:
    pass

from storpool import spconfig, spapi

from . import splocked


LOCKFILE = "/var/spool/openstack-storpool/openstack-attach.json"


class AttachDB(splocked.SPLockedJSONDB):
    def __init__(self, log, fname=LOCKFILE):
        # type: (AttachDB, logging.Logger, str) -> None
        super(AttachDB, self).__init__(fname)
        self._api = None  # type: Optional[spapi.Api]
        self._config = None  # type: Optional[spconfig.SPConfig]
        self._ourId = None  # type: Optional[int]
        self._volume_prefix = None  # type: Optional[str]
        self.LOG = log

    def config(self):
        # type: (AttachDB) -> spconfig.SPConfig
        if self._config is None:
            self._config = spconfig.SPConfig()
            self._ourId = int(self._config["SP_OURID"])
        return self._config

    def api(self):
        # type: (AttachDB) -> spapi.Api
        if self._api is None:
            self._api = spapi.Api.fromConfig(self.config())
        return self._api

    def volumePrefix(self):
        # type: (AttachDB) -> str
        if self._volume_prefix is None:
            cfg = self.config()
            self._volume_prefix = cfg.get("SP_OPENSTACK_VOLUME_PREFIX", "os")
        return self._volume_prefix

    def volumeName(self, id):
        # type: (AttachDB, str) -> str
        return "{pfx}--volume-{id}".format(pfx=self.volumePrefix(), id=id)

    def volsnapName(self, id, req_id):
        # type: (AttachDB, str, str) -> str
        return "{pfx}--volsnap-{id}--req-{req_id}".format(
            pfx=self.volumePrefix(), id=id, req_id=req_id
        )

    def snapshotName(self, type, id, more=None):
        # type: (AttachDB, str, str, Optional[str]) -> str
        return "{pfx}--{t}--{m}--snapshot-{id}".format(
            pfx=self.volumePrefix(),
            t=type,
            m="none" if more is None else more,
            id=id,
        )

    # TODO: cache at least the API attachments data
    def _get_attachments_data(
        self,  # type: AttachDB
    ):  # type: (...) -> Tuple[Dict[Text, Attach], List[spapi.AttachmentDesc]]
        pfx = self.volumePrefix()
        attached = [
            att
            for att in self.api().attachmentsList()
            if att.volume.startswith(pfx)
        ]
        return (self.get(), attached)

    def sync(self, req_id, detached):
        # type: (AttachDB, str, Optional[str]) -> None
        assert self._ourId is not None

        with self:
            (attach_req_d, apiatt) = self._get_attachments_data()

            attach = attach_req_d.get(req_id, None)
            if attach is None:
                if detached is not None:
                    # Ach, let's just hope for the best...
                    self.LOG.warn(
                        "StorPoolDriver._attach_sync() invoked for detaching "
                        "for unknown request {req}, ignored".format(req=req_id)
                    )
                    return
                raise Exception(
                    "StorPoolDriver._attach_sync() invoked for unknown "
                    "request {req}".format(req=req_id)
                )

            # OK, let's first see what *should be* attached
            vols = {}  # type: Dict[str, Attach]
            if detached is None:
                attach_req = list(attach_req_d.values())
            else:
                # Detaching this particular volume in this request?
                attach_req = [
                    att
                    for att in attach_req_d.values()
                    if att["volume"] != detached or att["id"] != req_id
                ]
            vol_to_reqs = collections.defaultdict(list)
            for att in attach_req:
                vname = att["volume"]
                vol_to_reqs[vname].append(att["id"])
                if vname not in vols or vols[vname]["rights"] < att["rights"]:
                    vols[vname] = {
                        "volume": vname,
                        "type": "n/a",
                        "id": "n/a",
                        "rights": att["rights"],
                        "volsnap": att.get("volsnap", False),
                        "remove_on_detach": att.get("remove_on_detach", False),
                    }

            # OK, let's see what *is* attached
            apiatt = [att for att in apiatt if att.client == self._ourId]
            attached = {
                att.volume: {
                    "volume": att.volume,
                    "type": "n/a",
                    "id": "n/a",
                    "rights": 2 if att.rights == "rw" else 1,
                    "volsnap": att.snapshot,
                    "remove_on_detach": False,
                }
                for att in apiatt
            }  # type: Dict[str, Attach]

            # Right, do we need to do anything now?
            all_vols = {v.name: True for v in self.api().volumesList()}
            all_sns = {s.name: True for s in self.api().snapshotsList()}
            vols_to_remove = []
            for v in vols.values():
                n = v["volume"]
                if n in attached and attached[n]["rights"] >= v["rights"]:
                    continue
                volsnap = v["volsnap"]
                if v["volume"] not in (all_sns if volsnap else all_vols):
                    vols_to_remove.append(v["volume"])
                    continue
                self._attach_and_wait(
                    client=self._ourId,
                    volume=n,
                    volsnap=volsnap,
                    rights=v["rights"],
                )

            # Clean up stale volume assignments
            if vols_to_remove:
                reqs_to_remove = []
                for vname in vols_to_remove:
                    reqs_to_remove.extend(vol_to_reqs[vname])
                if reqs_to_remove:
                    self.remove_keys(reqs_to_remove)

            # Finally, are we trying to detach anything?
            if detached in attached:
                self._detach_and_wait(
                    client=self._ourId,
                    volume=detached,
                    volsnap=attached[detached]["volsnap"],
                )

    def _attach_and_wait(self, client, volume, volsnap, rights):
        # type: (AttachDB, int, str, bool, int) -> None
        if volsnap:
            if rights > 1:
                raise spapi.ApiError(
                    "StorPool: cannot attach a snapshot in read/write mode"
                )
            self.api().volumesReassign(
                json=[{"snapshot": volume, "ro": [client]}]
            )
        else:
            mode = "rw" if rights == 2 else "ro"
            self.api().volumesReassign(
                json=[{"volume": volume, mode: [client]}]
            )
        devpath = "/dev/storpool/" + volume
        for i in range(10):
            if os.path.exists(devpath):
                break
            time.sleep(1)

    def _detach_and_wait(self, client, volume, volsnap):
        # type: (AttachDB, int, str, bool) -> None
        count = 10
        while True:
            try:
                force = count == 0
                if volsnap:
                    self.api().volumesReassign(
                        json=[
                            {
                                "snapshot": volume,
                                "detach": [client],
                                "force": force,
                            }
                        ]
                    )
                else:
                    self.api().volumesReassign(
                        json=[
                            {
                                "volume": volume,
                                "detach": [client],
                                "force": force,
                            }
                        ]
                    )
                break
            except spapi.ApiError as e:
                if e.name == "invalidParam" and "is open at" in e.desc:
                    assert count > 0
                    time.sleep(0.2)
                    count -= 1
