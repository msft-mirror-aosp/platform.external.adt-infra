import logging
import os
import re

import grpc
from google.protobuf import empty_pb2

from emu_test.proto.emulator_controller_pb2 import KeyboardEvent
from emu_test.proto.emulator_controller_pb2_grpc import EmulatorControllerStub
from emu_test.test_grpc.channel_provider import getEmulatorChannel

_EMPTY_ = empty_pb2.Empty()


class EmulatorService(object):
    """A simple wrapper around the emulator service."""

    def __init__(self, port, logger=logging.getLogger()):
        """Connect to the emulator on the given port, and log on the given logger."""
        self.channel = getEmulatorChannel(port)
        self.stub = EmulatorControllerStub(self.channel)
        self.logger = logger


    def sendText(self, text):
        self.stub.sendKey(KeyboardEvent(text=text))

    def sendKeyEvent(self, javascript_keycode, evt):
        """Sends a key event. """
        self.stub.sendKey(KeyboardEvent(key=javascript_keycode, eventType=evt))

    def sendKeyPress(self, javascript_keycode):
        """Sends the javascript keyo code as a single event."""
        self.sendKeyEvent(javascript_keycode, KeyboardEvent.keypress)
