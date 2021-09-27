#!/usr/bin/python3
"""Run a locking test between two processes."""

from __future__ import print_function

import os
import tempfile
import shutil
import socket
import sys

from typing import Tuple

if sys.version_info[0] < 3:
    import pathlib2 as pathlib  # pylint: disable=import-error
else:
    import pathlib

from storpool.spopenstack import (  # pylint: disable=wrong-import-position
    splocked,
)


def run_pid1(spipe, tempf):
    # type: (Tuple[int, int], pathlib.Path) -> None
    """Run the first child process."""
    print("p1: closing the other end of the pipe")
    spipe[1].close()

    print("p1: about to lock {tempf}".format(tempf=tempf))
    lockf = splocked.SPLockedJSONDB(str(tempf))
    with lockf:
        print("p1: about to lock it recursively")
        with lockf:
            print("p1: obtained the inner lock")
        print("p1: released the inner lock")

        print("p1: telling p2 we locked something")
        spipe[0].send(b"L")

        print("p1: waiting for p2 to tell us it failed")
        data = spipe[0].recv(1)
        print("p1: got {data!r}".format(data=data))
        if data != b"F":
            sys.exit("p1: expected p2 to tell us 'F' first")
        print("p1: about to unlock something")

    print("p1: telling p2 we unlocked something")
    spipe[0].send(b"U")

    print("p1: waiting for p2 to tell us it locked something")
    data = spipe[0].recv(1)
    print("p1: got {data!r}".format(data=data))
    if data != b"L":
        sys.exit("p1: expected p2 to tell us 'L'")

    print("p1: about to try to lock {tempf} again".format(tempf=tempf))
    try:
        with lockf:
            sys.exit("p1: why did we manage to lock it again?")
    except splocked.SPLockedFileError:
        print("p1: got an 'already locked' error")
        print("p1: tell p2 we failed to lock something")
        spipe[0].send(b"F")

    print("p1: waiting for p2 to tell us it unlocked something")
    data = spipe[0].recv(1)
    print("p1: got {data!r}".format(data=data))
    if data != b"U":
        sys.exit("p1: expected p2 to tell us 'U'")

    print("p1: done")


def run_pid2(spipe, tempf):
    # type: (Tuple[int, int], pathlib.Path) -> None
    """Run the second child process."""
    print("p2: closing the other end of the pipe")
    spipe[0].close()

    print(
        "p2: waiting for p1 to tell us it locked {tempf}".format(tempf=tempf)
    )
    data = spipe[1].recv(1)
    print("p2: got {data!r}".format(data=data))
    if data != b"L":
        sys.exit("p2: expected p1 to tell us 'L'")

    lockf = splocked.SPLockedJSONDB(str(tempf))

    print("p2: about to try to lock and fail")
    try:
        with lockf:
            sys.exit("p2: why did we manage to lock it?")
    except splocked.SPLockedFileError:
        print("p2: got an 'already locked' error")
        print("p2: tell p1 we failed to lock something")
        spipe[1].send(b"F")

    print("p2: waiting for p1 to tell us it unlocked something")
    data = spipe[1].recv(1)
    print("p2: got {data!r}".format(data=data))
    if data != b"U":
        sys.exit("p2: expected p1 to tell us 'U'")

    print("p2: about to lock {tempf}".format(tempf=tempf))
    with lockf:
        print("p2: about to lock it recursively")
        with lockf:
            print("p2: obtained the inner lock")
        print("p2: released the inner lock")

        print("p2: telling p1 we locked something")
        spipe[1].send(b"L")

        print("p2: waiting for p1 to tell us it failed")
        data = spipe[1].recv(1)
        print("p2: got {data!r}".format(data=data))
        if data != b"F":
            sys.exit("p2: expected p1 to tell us 'F'")

        print("p2: about to unlock something")

    print("p2: telling p1 we unlocked something")
    spipe[1].send(b"U")

    print("p2: done")


def main():
    # type: () -> None
    """Main program: spawn child processes, wait for them."""
    print("main: starting up with {path!r}".format(path=sys.executable))
    spipe = socket.socketpair(socket.AF_UNIX)
    print("main: created a pipe: {spipe!r}".format(spipe=spipe))

    in_main = True
    tempd = tempfile.mkdtemp(prefix="spopenstack-lock-")
    try:
        print(
            "main: using {tempd} as a temporary directory".format(tempd=tempd)
        )

        tempf = pathlib.Path(tempd) / "attach.json"
        print("main: creating {tempf}".format(tempf=tempf))
        tempf.write_text(u'{"source": "main"}', encoding="UTF-8")

        pid_1 = os.fork()
        if pid_1 == 0:
            in_main = False
            try:
                run_pid1(spipe, tempf)
            except (IOError, OSError, socket.error) as err:
                sys.exit("p1: something went wrong: {err}".format(err=err))
            print("p1: done")
            return
        print("main: started p1 at {pid_1}".format(pid_1=pid_1))

        pid_2 = os.fork()
        if pid_2 == 0:
            in_main = False
            try:
                run_pid2(spipe, tempf)
            except (IOError, OSError, socket.error) as err:
                sys.exit("p2: something went wrong: {err}".format(err=err))
            print("p2: done")
            return
        print("main: started p2 at {pid_2}".format(pid_2=pid_2))

        print("main: closing the pipe")
        spipe[0].close()
        spipe[1].close()

        print("main: waiting for p1")
        res_1 = os.waitpid(pid_1, 0)
        print("main: got p1 wait result {res_1}".format(res_1=res_1))

        print("main: waiting for p2")
        res_2 = os.waitpid(pid_2, 0)
        print("main: got p2 wait result {res_2}".format(res_2=res_2))

        if res_1 != (pid_1, 0) or res_2 != (pid_2, 0):
            sys.exit("main: something went wrong")
        print("main: done")
    finally:
        if in_main:
            print(
                "main: removing the {tempd} temporary directory".format(
                    tempd=tempd
                )
            )
            shutil.rmtree(tempd)


if __name__ == "__main__":
    main()
