"""
Contains a SnapshotService that can talk to the emulator snapshot service on the given grpc port.
"""
import logging
import time
import os
import re
from datetime import datetime
import grpc
from google.protobuf import empty_pb2

from emu_test.proto.waterfall_pb2 import CmdProgress, Cmd
from emu_test.proto.waterfall_pb2_grpc import WaterfallStub
from emu_test.test_grpc.channel_provider import getEmulatorChannel

_EMPTY_ = empty_pb2.Empty()


def cmd_stream(cmd):
    yield CmdProgress(cmd=Cmd(path=cmd, dir="/"))


class KeyEvent(object):
    """A parsed android KeyEvent entry."""

    def __init__(
        self,
        deviceId,
        source,
        displayId,
        action,
        flags,
        keyCode,
        scanCode,
        metaState,
        repeatCount,
        policyFlags,
        age,
    ):
        self.deviceId = deviceId
        self.source = source
        self.displayId = displayId
        self.action = action
        self.flags = flags
        self.keyCode = keyCode
        self.scanCode = scanCode
        self.metaState = metaState
        self.repeatCount = repeatCount
        self.policyFlags = policyFlags
        self.age = int((time.time() + 0.5) * 1000) - int(float(age))

    def __str__(self):
        return "{}, {}, {}".format(
            self.keyCode, self.action, datetime.fromtimestamp(float(self.age) / 1000)
        )


class WaterfallService(object):
    """A simple wrapper around the waterfall service.

       This class exposes a series of adb like commands that are executed.
    """

    KEVENT_LINE = re.compile(
        r"\s*KeyEvent\(deviceId=(\d+), source=(.*), displayId=(.*), action=(UP|DOWN), flags=(.*), keyCode=(.*), scanCode=(.*), metaState=(.*), repeatCount=(\d+)\), policyFlags=(.*), age=(\d+.\d+)ms\s*"
    )

    def __init__(self, port, logger=logging.getLogger()):
        """Connect to the emulator on the given port, and log on the given logger."""
        self.channel = getEmulatorChannel(port)
        self.stub = WaterfallStub(self.channel)
        self.logger = logger

    def get_latest_keyevents(self, nr=4):
        """This gets a list of the latest #nr keyevents by calling dumpsys, note you can see old events!"""
        sout, serr, exitcode = ("", "", 0)
        it = self.stub.Exec(
            cmd_stream(
                "/system/bin/dumpsys input | grep KeyEvent | tail -n {}".format(nr)
            )
        )
        for msg in it:
            sout += msg.stdout
            serr += msg.stderr
            exitcode = msg.exit_code

        # Parse this:
        #   KeyEvent(deviceId=0, source=0x00000101, displayId=-1, action=DOWN, flags=0x00000008, keyCode=187, scanCode=580, metaState=0x00000000, repeatCount=0), policyFlags=0x62000000, age=1964.6ms
        #   KeyEvent(deviceId=0, source=0x00000101, displayId=-1, action=UP, flags=0x00000008, keyCode=187, scanCode=580, metaState=0x00000000, repeatCount=0), policyFlags=0x62000000, age=1964.3ms
        events = []
        for line in sout.splitlines():
            m = WaterfallService.KEVENT_LINE.match(line)
            if m:
                events.append(
                    KeyEvent(
                        m.group(1),
                        m.group(2),
                        m.group(3),
                        m.group(4),
                        m.group(5),
                        m.group(6),
                        m.group(7),
                        m.group(8),
                        m.group(9),
                        m.group(10),
                        m.group(11),
                    )
                )
            else:
                self.logger.warn("Ignoring %s", line)

        self.logger.info("Received: %s", " ".join([str(x) for x in events]))
        return events
