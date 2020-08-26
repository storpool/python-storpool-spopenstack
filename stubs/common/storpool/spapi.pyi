from typing import Dict, List, Optional, Union

from . import spconfig


class ApiError(Exception):

    name: str
    desc: str


class AttachmentDesc(object):

    client: int
    volume: str
    rights: str
    snapshot: bool

    def __init__(self, client: int, volume: str, rights: str, snapshot: bool) -> None: ...


AttachmentDescDict = Dict[str, Union[str, bool, List[Union[str, int]]]]


class VolumeReassignDesc(object):

    volume: str
    detach: List[Union[int, str]]
    ro: List[int]
    rw: List[int]
    force: bool


class VolumeSummary(object):

    name: str

    def __init__(self, name: str) -> None: ...


class SnapshotSummary(object):

    name: str

    def __init__(self, name: str) -> None: ...


class Api(object):

    port: int

    @classmethod
    def fromConfig(cls, cfg: Optional[spconfig.SPConfig] = None) -> Api: ...

    def attachmentsList(self) -> List[AttachmentDesc]: ...
    def snapshotsList(self) -> List[SnapshotSummary]: ...
    def volumesList(self) -> List[VolumeSummary]: ...
    def volumesReassign(self, json: List[AttachmentDescDict]) -> None: ...

    # And now for the test fixtures...

    volumes: List[VolumeSummary]
    snapshots: List[SnapshotSummary]
    attachments: List[AttachmentDesc]
    reassign: List[List[AttachmentDescDict]]
