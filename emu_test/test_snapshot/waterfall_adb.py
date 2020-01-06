"""
Contains a SnapshotService that can talk to the emulator snapshot service on the given grpc port.
"""
import logging
import os

import grpc
from google.protobuf import empty_pb2

# from emu_test.proto.waterfall_pb2 import Snapshot
from emu_test.proto.waterfall_pb2 import CmdProgress, Cmd
from emu_test.proto.waterfall_pb2_grpc import WaterfallStub
from emu_test.test_snapshot.channel_provider import getEmulatorChannel

_EMPTY_ = empty_pb2.Empty()


def cmd_stream(cmd):
    yield CmdProgress(cmd=Cmd(path=cmd, dir="/"))

class WaterfallService(object):
    """A simple wrapper around the waterfall service."""

    def __init__(self, port, logger=logging.getLogger()):
        """Connect to the emulator on the given port, and log on the given logger."""
        self.channel = getEmulatorChannel(port)
        self.stub = WaterfallStub(self.channel)
        self.logger = logger


    def get_props(self):
        sout, serr, exitcode = ("","",0)
        it = self.stub.Exec(cmd_stream("/system/bin/getprop"))
        for msg in it:
            sout += msg.stdout
            serr += msg.stderr
            exitcode = msg.exit_code
        self.logger.debug("stdout: %s, stderr: %s, exit: %d", sout, serr, exitcode)
        return sout, serr, exitcode