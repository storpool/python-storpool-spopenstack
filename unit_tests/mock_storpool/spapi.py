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
""" Mock the storpool.spapi.* classes for testing """

try:
    from typing import Any, Dict, List, Optional, Union

    AttachmentDescDict = Dict[str, Union[str, bool, List[Union[str, int]]]]
except ImportError:
    pass


# pylint: disable=too-few-public-methods
class ApiError(Exception):
    """ Mock the class for errors returned by API requests. """

    def __init__(self, status, json=None):
        # type: (ApiError, Any, Optional[Dict[str, Dict[str, Any]]]) -> None
        super(ApiError, self).__init__()
        self.status = status
        self.json = (
            json
            if json is not None
            else {
                "error": {
                    "name": "invalidParam",
                    "descr": "oof",
                    "transient": False,
                }
            }
        )
        err = self.json.get("error", {})
        self.desc = err.get("descr", "oof")
        self.name = err.get("name", "invalidParam")
        self.transient = err.get("transient", False)

    def __str__(self):
        # type: (ApiError) -> str
        return "{0}: {1}".format(self.name, self.desc)


class VolumeSummary(object):
    """ Mock an API volume. """

    def __init__(self, name):
        # type: (VolumeSummary) -> None
        self.name = name


class SnapshotSummary(object):
    """ Mock an API snapshot. """

    def __init__(self, name):
        # type: (SnapshotSummary) -> None
        self.name = name


class AttachmentDesc(object):
    """ Mock an API record about an attached volume or snapshot. """

    def __init__(self, volume, client, snapshot, rights):
        # type: (AttachmentDesc, str, int, str, str) -> None
        self.volume = volume
        self.client = client
        self.snapshot = snapshot
        self.rights = rights


class Api(object):
    """ Mock the API bindings class. """

    def __init__(self, host, port, auth):
        # type: (Api, str, int, str) -> None
        """ Initialize an API bindings object. """
        self.host = host
        self.port = port
        self.auth = auth
        self.reassign = []  # type: List[List[AttachmentDescDict]]

        self.volumes = []  # type: List[VolumeSummary]
        self.snapshots = []  # type: List[SnapshotSummary]
        self.attachments = []  # type: List[AttachmentDesc]

    @classmethod
    def fromConfig(cls, cfg, **kwargs):  # pylint: disable=invalid-name
        # type: (Dict[str, str], Dict[str, Any]) -> Api
        """ Initialize an API bindings object with the supplied config. """
        return cls(  # type: ignore
            host=cfg["SP_API_HTTP_HOST"],
            port=int(cfg["SP_API_HTTP_PORT"]),
            auth=cfg["SP_AUTH_TOKEN"],
            **kwargs
        )

    def volumesReassign(self, json):  # pylint: disable=invalid-name
        # type: (Api, List[AttachmentDescDict]) -> None
        """ Record the arguments passed to a volumesReassign() call. """
        self.reassign.append(json)

    def attachmentsList(self):  # pylint: disable=invalid-name
        # type: (Api) -> List[AttachmentDesc]
        """ Return the list of attachments specified by the test. """
        return list(self.attachments)

    def volumesList(self):  # pylint: disable=invalid-name
        # type: (Api) -> List[VolumeSummary]
        """ Return the list of volumes specified by the test. """
        return list(self.volumes)

    def snapshotsList(self):  # pylint: disable=invalid-name
        # type: (Api) -> List[SnapshotSummary]
        """ Return the list of snapshots specified by the test. """
        return list(self.snapshots)
