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
""" Mock the storpool.spapi.* classes for testing """


# pylint: disable=too-few-public-methods
class ApiError(Exception):
    """ Mock the class for errors returned by API requests. """

    def __init__(self, status, json=None):
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
        return "{0}: {1}".format(self.name, self.desc)


class Volume(object):
    """ Mock an API volume. """

    def __init__(self, name):
        self.name = name


class Snapshot(object):
    """ Mock an API snapshot. """

    def __init__(self, name):
        self.name = name


class Attachment(object):
    """ Mock an API record about an attached volume or snapshot. """

    def __init__(self, volume, client, snapshot, rights):
        self.volume = volume
        self.client = client
        self.snapshot = snapshot
        self.rights = rights


class Api(object):
    """ Mock the API bindings class. """

    def __init__(self, host, port, auth):
        """ Initialize an API bindings object. """
        self.host = host
        self.port = port
        self.auth = auth
        self.reassign = []

        self.volumes = []
        self.snapshots = []
        self.attachments = []

    def volumesReassign(self, json):  # pylint: disable=invalid-name
        """ Record the arguments passed to a volumesReassign() call. """
        self.reassign.append(json)

    def attachmentsList(self):  # pylint: disable=invalid-name
        """ Return the list of attachments specified by the test. """
        return list(self.attachments)

    def volumesList(self):  # pylint: disable=invalid-name
        """ Return the list of volumes specified by the test. """
        return list(self.volumes)

    def snapshotsList(self):  # pylint: disable=invalid-name
        """ Return the list of snapshots specified by the test. """
        return list(self.snapshots)
