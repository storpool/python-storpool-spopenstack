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
A trivial JSON key/value store protected by a lockfile.
"""

import errno
import json
import os
import posix
import threading
import time

try:
    import types

    from typing import Any, Dict, Iterable, Optional, Text, Type, TypeVar

    TExc = TypeVar("TExc", bound=BaseException)
except ImportError:
    pass


rlock = threading.RLock()


class SPLockedFile(object):
    def __init__(self, fname):
        # type: (SPLockedFile, str) -> None
        self._fname = fname
        self._lockfname = self._fname + ".splock"
        self._lockfd = None  # type: Optional[int]
        self._last = None  # type: Optional[posix.stat_result]
        self._count = 0

    def changed(self):
        # type: (SPLockedFile) -> bool
        last = self._last
        try:
            st = os.stat(self._fname)
        except OSError:
            if last is not None:
                self._last = None
                return True
            else:
                return False
        if last is None:
            return True

        assert isinstance(st, posix.stat_result)
        assert isinstance(last, posix.stat_result)
        return (
            st.st_ino != last.st_ino
            or st.st_mtime != last.st_mtime
            or st.st_size != last.st_size
        )

    def __enter__(self):
        # type: (SPLockedFile) -> None
        rlock.acquire()
        self._count += 1

        if self._count > 1:
            assert self._lockfd is not None
            return

        assert self._lockfd is None
        for x in range(100):
            try:
                f = os.open(self._lockfname, os.O_CREAT | os.O_EXCL, 0o600)
                break
            except OSError as e:
                if e.errno == errno.EEXIST:
                    time.sleep(0.1)
                else:
                    raise
        else:
            raise Exception(
                "Could not lock the {f} file (using {fl})".format(
                    f=self._fname, fl=self._lockfname
                )
            )
        assert f is not None
        self._lockfd = f

    def __exit__(
        self,  # type: SPLockedFile
        etype,  # type: Optional[Type[TExc]]
        eval,  # type: Optional[TExc]
        tb,  # type: Optional[types.TracebackType]
    ):  # type: (...) -> None
        if self._count > 1:
            self._count -= 1
            rlock.release()
            return

        assert self._lockfd is not None
        os.close(self._lockfd)
        self._lockfd = None

        # If no exceptions have been raised, update the stat(2) cache
        if etype is None:
            try:
                self._last = os.stat(self._fname)
            except OSError:
                self._last = None

        try:
            os.remove(self._lockfname)
        except OSError:
            pass

        self._count -= 1
        rlock.release()

    def jsload(self):
        # type: (SPLockedFile) -> Any
        with self:
            with open(self._fname, "r") as f:
                return json.loads(f.read())

    def jsdump(self, obj):
        # type: (SPLockedFile, Any) -> None
        with self:
            with open(self._fname, "w") as f:
                f.write(json.dumps(obj))


class SPLockedJSONDB(SPLockedFile):
    def __init__(self, fname):
        # type: (SPLockedJSONDB, str) -> None
        super(SPLockedJSONDB, self).__init__(fname)
        self._data = None  # type: Optional[Dict[Text, Any]]

    def get(self):
        # type: (SPLockedJSONDB) -> Dict[Text, Any]
        with self:
            if self._data is None or self.changed():
                try:
                    self._data = self.jsload()
                except IOError as e:
                    # No such file or directory?
                    if e.errno == errno.ENOENT:
                        self._data = {}
                    else:
                        raise

            assert self._data is not None
            return self._data

    def add(self, key, val):
        # type: (SPLockedJSONDB, Text, Any) -> None
        with self:
            d = self.get()
            d[key] = val
            self.jsdump(d)

    def remove(self, key):
        # type: (SPLockedJSONDB, Text) -> None
        self.remove_keys([key])

    def remove_keys(self, keys):
        # type: (SPLockedJSONDB, Iterable[Text]) -> None
        with self:
            d = self.get()
            changed = False
            for key in keys:
                if key in d:
                    del d[key]
                    changed = True
            if changed:
                self.jsdump(d)
