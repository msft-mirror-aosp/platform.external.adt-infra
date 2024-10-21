# Copyright 2020 The Android Open Source Project
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
import random
import re
import string
import time

import pytest
from aemu.proto.emulator_controller_pb2 import KeyboardEvent
from aemu.proto.emulator_controller_pb2_grpc import EmulatorControllerStub

# Parse emulator log.
EMU_MANY_KEY_EVENT = re.compile(r".* (\d+): sendKeyCodes: \[([0-9a-fA-F ,]+)\]")
EMU_SINGLE_KEY_EVENT = re.compile(r".* (\d+): sendKeyCode: (\d+)")

EV_DEV_LETTERS = {
    "A": 0x001E,
    "B": 0x0030,
    "C": 0x002E,
    "D": 0x0020,
    "E": 0x0012,
    "F": 0x0021,
    "G": 0x0022,
    "H": 0x0023,
    "I": 0x0017,
    "J": 0x0024,
    "K": 0x0025,
    "L": 0x0026,
    "M": 0x0032,
    "N": 0x0031,
    "O": 0x0018,
    "P": 0x0019,
    "Q": 0x0010,
    "R": 0x0013,
    "S": 0x001F,
    "T": 0x0014,
    "U": 0x0016,
    "V": 0x002F,
    "W": 0x0011,
    "X": 0x002D,
    "Y": 0x0015,
    "Z": 0x002C,
    "SHIFT": 0x002A,
}


def wait_for_keyboard(event_stream, ev_code, timeout=10):
    """Wait for the evdev value to occur in the given event stream

    Args:
        event_stream: A queue that produces log lines which contain
          ev dev values.
        ev_code: The evdev code we are looking for.
        timeout: Maximum time in seconds we are willing to wait.

    Returns:
         the time in epoch seconds when this event occurred, or 0
         if the event did not arrive before the timeout was reached.
    """
    until = time.time() + timeout
    while time.time() < until:
        while not event_stream.empty():
            line = event_stream.get(False)
            entry = EMU_MANY_KEY_EVENT.match(line)
            if entry:
                codes = [int(x, 16) for x in entry.group(2).split(",")]
                if ev_code in codes:
                    return int(entry.group(1)) / 1000000
            entry = EMU_SINGLE_KEY_EVENT.match(line)
            if entry and ev_code == int(entry.group(2)):
                return int(entry.group(1)) / 1000000

    return 0


def send_grpc_letter(avd, letter):
    """Sends a letter using gRPC.

    Args:
       letter: The letter to send
    """
    grpc = EmulatorControllerStub(emulator.channel)
    grpc.sendKey(KeyboardEvent(text=letter))


def send_telnet_letter(avd, letter):
    """Sends a mouse click using the telnet console.

    Args:
       letter: The letter to send
    """
    telnet = avd.get_telnet()
    telnet.send("event text {}".format(letter))


def send_letter_over(send_fn, avd, log):
    """Send and random letter and wait until the event was registered.

    Args:
        send_fn: function used to send the letter
        avd: The emulator
        log: A queue to the emulator log.

    Returns:
        Time taken for the event to be delivered.
    """

    while not log.empty():
        log.get(False)
    letter = random.choice(string.ascii_letters)
    send_time = time.time()
    send_fn(avd, letter)
    delivery_time = wait_for_keyboard(log, EV_DEV_LETTERS[letter.upper()])
    return delivery_time - send_time


@pytest.mark.hostperf
@pytest.mark.benchmark(group="letter-host-host")
def test_letter_perf_host_host_grpc(emulator_log, benchmark_stat):
    """Checks that we can send keyboard events over grpc.

    This measures timestamp before calling send - observed timestamp at receipt in
    host. This test will be skipped if you are using a debug emulator.

    It will:
       send mouse click
       wait until emulator_log in host log sees an event.
    """
    # This test can only run if we launched the emulator
    if not emulator_log:
        pytest.skip()

    for i in range(0, 40):
        benchmark_stat.update(send_letter_over(send_grpc_letter, emulator_log))


@pytest.mark.hostperf
@pytest.mark.benchmark(group="letter-host-host")
def test_letter_perf_host_host_telnet(avd, emulator_log, benchmark_stat):
    """Checks that we can send keyboard events over telnet.

    This measures timestamp before calling send - observed timestamp at receipt in
    host. This test will be skipped if you are using a debug emulator.

    It will:
       send a letter
       wait until emulator_log in host log sees an event.
    """
    # This test can only run if we launched the emulator
    if not emulator_log:
        pytest.skip("Likely running under debugger without logger")

    for i in range(0, 40):
        benchmark_stat.update(send_letter_over(send_telnet_letter, avd, emulator_log))
