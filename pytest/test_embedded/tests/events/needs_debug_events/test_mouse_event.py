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

import pytest
from aemu.proto.emulator_controller_pb2 import MouseEvent

from tests.fixtures.benchmark_event_fixtures import EventTimeTester


async def send_grpc_click(avd, x, y, buttons):
    """Sends a mouse click using gRPC.

    Args:
        x: The x coordinate
        y: The y coordinate
        buttons: The number of buttons.
    """
    controller = EmulatorControllerStub(avd.channel)
    await controller.sendMouse(MouseEvent(x=x, y=y, buttons=buttons))


async def send_telnet_click(avd, x, y, buttons):
    """Sends a mouse click using the telnet console.

    Args:
        x: The x coordinate
        y: The y coordinate
        buttons: The number of buttons.
    """
    await avd.get_telnet().send("event mouse {} {} 0 {}".format(x, y, buttons))


def send_mouse_over(tester):
    """Send and random mouse event using an EventTimeTester and wait until
       the event was registered.

    Args:
        tester: An event time tester used to send and wait for the event to
          arrive.

    Returns:
        Time taken for the event to be delivered.
    """
    x = random.randint(100, 900)
    y = random.randint(200, 1200)
    return tester.send_mouse_and_wait_until_recv(x, y, 1)


@pytest.mark.hostperf
@pytest.mark.benchmark(group="mouse-wall")
@pytest.mark.skipos(
    "all", "Wall time measurements with adb are flaky and not supported beyond P."
)
@pytest.mark.skip("perf tests need to be explicitly selected")
def test_mouse_perf_wall_grpc(avd, android_start_time, adb_event_stream, benchmark):
    """Checks that we can send mouse events over gRPC.

    This measures wall clock time of the send_mouse_over function.
    It will:
       send mouse click
       wait until adb_event_stream in guest sees the event.
    """
    tester = EventTimeTester(avd, send_grpc_click, adb_event_stream, android_start_time)
    benchmark(send_mouse_over, tester=tester)


@pytest.mark.hostperf
@pytest.mark.hardware
@pytest.mark.benchmark(group="mouse-wall")
@pytest.mark.skipos(
    "all", "Wall time measurements with adb are flaky and not supported beyond P."
)
@pytest.mark.skip("perf tests need to be explicitly selected")
def test_mouse_perf_wall_telnet(avd, android_start_time, adb_event_stream, benchmark):
    """Checks that we can send mouse events over telnet.

    This measures wall clock time of the send_mouse_over function.
    It will:
       send mouse click
       wait until adb_event_stream in guest sees the event.
    """
    tester = EventTimeTester(
        avd, send_telnet_click, adb_event_stream, android_start_time
    )
    benchmark(send_mouse_over, tester=tester)


@pytest.mark.hostperf
@pytest.mark.benchmark(group="mouse-host-guest")
@pytest.mark.skipos(
    "all", "Wall time measurements with adb are flaky and not supported beyond P."
)
@pytest.mark.skip("perf tests need to be explicitly selected")
def test_mouse_perf_host_guest_telnet(
    avd, android_start_time, adb_event_stream, benchmark_stat
):
    """Checks that we can send mouse events over telnet.

    This measures timestamp before calling send - observed timestamp at receipt in
    guest. This is completely bogus due to clock skew between guest and host,
    but the results *might* be comparable between telnet/grpc.


    It will:
       send mouse click
       wait until adb_event_stream in guest sees the event.
    """
    tester = EventTimeTester(
        avd, send_telnet_click, adb_event_stream, android_start_time
    )
    for i in range(0, 40):
        benchmark_stat.update(send_mouse_over(tester))


@pytest.mark.hostperf
@pytest.mark.benchmark(group="mouse-host-guest")
@pytest.mark.skipos(
    "all", "Wall time measurements with adb are flaky and not supported beyond P."
)
@pytest.mark.skip("perf tests need to be explicitly selected")
def test_mouse_perf_host_guest_grpc(
    avd, android_start_time, adb_event_stream, benchmark_stat
):
    """Checks that we can send mouse events over grpc.

    This measures timestamp before calling send - observed timestamp at receipt in
    guest. This is completely bogus due to clock skew between guest and host,
    but the results *might* be comparable between telnet/grpc.


    It will:
       send mouse click
       wait until adb_event_stream in guest sees the event.
    """
    tester = EventTimeTester(avd, send_grpc_click, adb_event_stream, android_start_time)
    for i in range(0, 40):
        benchmark_stat.update(send_mouse_over(tester))


@pytest.mark.hostperf
@pytest.mark.benchmark(group="mouse-host-host")
@pytest.mark.skip("perf tests need to be explicitly selected")
def test_mouse_perf_host_host_grpc(avd, emulator_log, benchmark_stat):
    """Checks that we can send mouse events over grpc.

    This measures timestamp before calling send - observed timestamp at receipt in
    host. This test will be skipped if you are using a debug emulator.

    It will:
       send mouse click
       wait until adb_event_stream in host log sees the event.
    """
    # This test can only run if we launched the emulator
    if not emulator_log:
        pytest.skip("Likely running under debugger without logger")

    tester = EventTimeTester(avd, send_grpc_click, emulator_log, 0)
    for i in range(0, 40):
        benchmark_stat.update(send_mouse_over(tester))


@pytest.mark.hostperf
@pytest.mark.benchmark(group="mouse-host-host")
@pytest.mark.skip("perf tests need to be explicitly selected")
def test_mouse_perf_host_host_telnet(avd, emulator_log, benchmark_stat):
    """Checks that we can send mouse events over telnet.

    This measures timestamp before calling send - observed timestamp at receipt in
    host. This test will be skipped if you are using a debug emulator.

    It will:
       send mouse click
       wait until adb_event_stream in host log sees the event.
    """
    # This test can only run if we launched the emulator
    if not emulator_log:
        pytest.skip("Likely running under debugger without logger")

    tester = EventTimeTester(avd, send_telnet_click, emulator_log, 0)
    for i in range(0, 40):
        benchmark_stat.update(send_mouse_over(tester))
