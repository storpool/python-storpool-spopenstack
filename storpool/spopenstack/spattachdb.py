#
# -
# Copyright (c) 2014, 2015, 2019  StorPool.
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

from storpool import spconfig, spapi

from . import splocked


class AttachDB(splocked.SPLockedJSONDB):
    def __init__(
        self,
        fname="/var/spool/openstack-storpool/openstack-attach.json",
        log=None,
    ):
        super(AttachDB, self).__init__(fname)
        self._api = None
        self._config = None
        self._ourId = None
        self._volume_prefix = None
        self.LOG = log

    def config(self):
        if self._config is None:
            self._config = spconfig.SPConfig()
            self._ourId = int(self._config["SP_OURID"])
        return self._config

    def api(self):
        if self._api is None:
            cfg = self.config()
            self._api = spapi.Api(
                host=cfg["SP_API_HTTP_HOST"],
                port=cfg["SP_API_HTTP_PORT"],
                auth=cfg["SP_AUTH_TOKEN"],
            )
        return self._api

    def volumePrefix(self):
        if self._volume_prefix is None:
            cfg = self.config()
            self._volume_prefix = cfg.get("SP_OPENSTACK_VOLUME_PREFIX", "os")
        return self._volume_prefix

    def volumeName(self, id):
        return "{pfx}--volume-{id}".format(pfx=self.volumePrefix(), id=id)

    def volsnapName(self, id, req_id):
        return "{pfx}--volsnap-{id}--req-{req_id}".format(
            pfx=self.volumePrefix(), id=id, req_id=req_id
        )

    def snapshotName(self, type, id, more=None):
        return "{pfx}--{t}--{m}--snapshot-{id}".format(
            pfx=self.volumePrefix(),
            t=type,
            m="none" if more is None else more,
            id=id,
        )

    # TODO: cache at least the API attachments data
    def _get_attachments_data(self):
        pfx = self.volumePrefix()
        attached = filter(
            lambda att: att.volume.startswith(pfx),
            self.api().attachmentsList(),
        )
        return (self.get(), attached)

    def sync(self, req_id, detached):
        with self:
            (attach_req, apiatt) = self._get_attachments_data()

            attach = attach_req.get(req_id, None)
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
            vols = {}
            if detached is None:
                attach_req = attach_req.values()
            else:
                # Detaching this particular volume in this request?
                attach_req = [
                    att
                    for att in attach_req.values()
                    if att["volume"] != detached or att["id"] != req_id
                ]
            vol_to_reqs = collections.defaultdict(list)
            for att in attach_req:
                v = att["volume"]
                vol_to_reqs[v].append(att["id"])
                if v not in vols or vols[v]["rights"] < att["rights"]:
                    vols[v] = {
                        "volume": v,
                        "volsnap": att.get("volsnap", False),
                        "rights": att["rights"],
                    }

            # OK, let's see what *is* attached
            apiatt = filter(lambda att: att.client == self._ourId, apiatt)
            attached = dict(
                map(
                    lambda att: (
                        att.volume,
                        {
                            "volume": att.volume,
                            "rights": 2 if att.rights == "rw" else 1,
                            "snapshot": att.snapshot,
                        },
                    ),
                    apiatt,
                )
            )

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
                for v in vols_to_remove:
                    reqs_to_remove.extend(vol_to_reqs[v])
                if reqs_to_remove:
                    self.remove_keys(reqs_to_remove)

            for v in attached.values():
                n = v["volume"]
                if n in vols:
                    volsnap = vols[n]["volsnap"]
                    if vols[n]["rights"] < v["rights"]:
                        self._attach_and_wait(
                            client=self._ourId,
                            volume=n,
                            volsnap=volsnap,
                            rights=vols[n]["rights"],
                        )
                else:
                    self._detach_and_wait(
                        client=self._ourId, volume=n, volsnap=v["snapshot"]
                    )

    def _attach_and_wait(self, client, volume, volsnap, rights):
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
