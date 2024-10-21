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
"""Fixtures for measuring performance."""
import collections
import logging
import re
import time

import pytest
from pytest_benchmark.stats import Metadata

from tests.test_utils import time_to_str


@pytest.fixture
def benchmark_stat(request):
    """A Test fixture that gives a single benchmark statistics entry.

    You can update the stats with your results for your test run.

    For example:

    test_my_test(benchmark_stat):
      for i in range(0, 10):
        time_in_seconds = 0.001
        benchmark_stat.update(time_in_seconds)

    Your results will be included in the final report.
    """
    bs = request.config._benchmarksession
    node = request.node

    marker = node.get_closest_marker("benchmark")
    options = dict(marker.kwargs) if marker else {}

    Fixture = collections.namedtuple(
        "Fixture", "name fullname group param params extra_info cprofile_stats"
    )
    param = None
    params = None

    if hasattr(node, "callspec"):
        param = node.callspec.id
        params = node.callspec.params

    fixture = Fixture(
        name=node.name,
        fullname=node._nodeid,
        group=options.get("group", None),
        param=param,
        params=params,
        extra_info={},
        cprofile_stats=None,
    )
    bench_stats = Metadata(
        fixture,
        iterations=1,
        # Options are all unused, and here only to make
        # the Metadata complete.
        options={
            "disable_gc": True,
            "timer": None,
            "min_rounds": 1,
            "max_time": 20,
            "min_time": 2,
            "warmup": None,
        },
    )
    bs.benchmarks.append(bench_stats)
    return bench_stats


@pytest.fixture
def adb_event_stream(avd):
    """Streamed output of adb getevent -t.

    The stream will consume all initial events, and should be ready
    for all incoming events when it returns.

    Note: Needs android-Q or higher.
    """
    with avd.adb.stream("shell getevent", "-t") as events:
        found_evt = False
        # Make sure we skip the initial diagnostics.
        while not found_evt:
            found_evt = "Power Button" in events.get()

        # Flush any remaining events.
        while not events.empty():
            events.get(False)

        yield events


_android_start_time = None


@pytest.fixture
def android_start_time(avd):
    """Returns the approx starting time of the linux kernel in seconds, it does so
       by averaging out a series of starting estimates.

    Returns:
        Epoch in seconds when the emulator started with ms accuracy.
    """

    def _get_approx_start_time():
        """Returns the approx starting time of the linux kernel in seconds.

            The start time is approximated by getting $EPOCHREALTIME and proc/uptime
            from the emulator. Note that uptime only provides ms accuracy.

        Returns:
            Epoch in seconds when the emulator started.
        """
        # Epoch realtime is tv.sec.tv_usec, /proc/uptime is tv.sec.msec
        info = adb_shell("echo $EPOCHREALTIME $(cat /proc/uptime)")
        epoch_s, uptime_s, _ = info.split(" ")
        start_time = float(epoch_s) - float(uptime_s)
        logging.info("Kernel started at +/- %s", time_to_str(start_time))
        return start_time

    global _android_start_time
    if _android_start_time is not None:
        return _android_start_time

    launch_times = [_get_approx_start_time() for i in range(0, 50)]
    _android_start_time = sum(launch_times) / len(launch_times)
    return _android_start_time


class EventTimeTester(object):
    """Tests how long it takes to deliver an event.

    Measurements are done by:

    - Checking timestamps on getevent stream from guest
    - Checking timestamps on the emulator log (host) (need -debug-events flag)
    - Checking time to read event from getevent stream
    """

    # Parse getevent -t output
    GET_EVENT = re.compile(
        r"\[\s+(\d+\.\d+)\] /dev/input/.*: ([0-9a-f]+) ([0-9a-f]+) ([0-9a-f]+)"
    )

    # Parse emulator log.
    EMU_EVENT = re.compile(
        r".* (\d+): sendGenericEvent: \[\s+([0-9a-fA-F]+),\s+([0-9a-fA-F]+),\s+([0-9a-fA-F]+),\s+(-?[0-9a-fA-F]+)\]"
    )

    def __init__(self, emulator, send_fn, event_stream, start_time_seconds):
        """Creates an EventTimeTester object.

        Args:
            send_fn: Function used to send an (x, y, buttons) mouse click to
              the emulator
            event_stream: Event stream where we can observe the arrived events.
            start_time_seconds: The start time of the emulator in seconds, only needed
              when receiving events from an adb_event_stream
        """
        self.width = emulator.width
        self.height = emulator.height
        self.emulator = emulator
        self.send_fn = send_fn
        self.event_stream = event_stream
        self.start_time = start_time_seconds

    def parse_event_time(self, event_line):
        """Parse an ev dev event logline.

        There are 2 sources for this:

        - getevent -t, run inside the guest
        - emulator logs, (when launched with -debug-events)

        Args:
            event_line: The line from the log that needs to be parsed.

        Returns:
            A tuple containing the following:
            (time_in_seconds, type, code, value)

            or None if no ev dev event was found.
        """
        m = EventTimeTester.GET_EVENT.match(event_line)
        if m:
            return (
                self.start_time
                + float(m.group(1)),  # tv.sec + tv.u_sec since kernel start.
                int(m.group(2), 16),
                int(m.group(3), 16),
                int(m.group(4), 16),
            )
        m = EventTimeTester.EMU_EVENT.match(event_line)
        if m:
            return (
                int(m.group(1)) / 1000000,
                int(m.group(2), 16),
                int(m.group(3), 16),
                int(m.group(4), 16),
            )

    def scale_axis(self, value, min_in, max_in):
        """Scales a value along the ev_dev axis.

        Returns:
            A scaled value between 0x0 - 0x07FFF used as ev_dev value.
        """
        min_out = 0  #
        max_out = 0x7FFF  # EV_ABS_MAX;
        range_out = max_out - min_out
        range_in = max_in - min_in
        if range_in < 1:
            return min_out + range_out / 2

        return int((value - min_in) * range_out / range_in + min_out)

    def sequence_contains_sequence(self, haystack_seq, needle_seq):
        """ "True if the needle_sequence occurs in the haystack."""
        for i in range(0, len(haystack_seq) - len(needle_seq) + 1):
            if needle_seq == haystack_seq[i : i + len(needle_seq)]:
                return i

    def wait_for_events(self, look_for, event_stream, timeout=10):
        """Wait for the sequence to occur in the given event stream

        Args:
            look_for: Sequence of ev dev tuples (type, code, value) we
              are looking for in the event stream
            event_stream: A queue that produces log lines which contain
              ev dev values.
            timeout: Maximum time in seconds we are willing to wait.

        Returns:
             the time in epoch seconds when this event occurred, or 0
             if the event did not arrive before the timeout was reached.
        """
        search = []
        idx = None
        until = time.time() + timeout
        while idx is None and time.time() < until:
            while not event_stream.empty():
                line = event_stream.get(False)
                entry = self.parse_event_time(line)
                if entry:
                    search.append(entry)

            # Now check if the sequence contains what we are looking for.
            idx = self.sequence_contains_sequence(
                [(x[1], x[2], x[3]) for x in search], look_for
            )

        if idx is not None:
            return search[idx][0]
        return 0

    def send_mouse_and_wait_until_recv(self, x, y, buttons):
        """Sends the a mouse click and waits until it was received.

        Returns:
            Time it took for the event to arrive.
        """
        look_for = self.expect_mouse_sequence(x, y, buttons)
        send_time = time.time()
        self.send_fn(self.emulator, x, y, buttons)

        # Note you would expect delivery_at > send_time
        # however due to clock skew between guest and host
        # it is entirely possible to deliver before sending if you
        # are observering events in the guest!
        delivery_at = self.wait_for_events(look_for, self.event_stream)
        time_spend = delivery_at - send_time

        logging.info(
            "Event received was send at: %s and received at %s, after %s seconds.",
            time_to_str(send_time),
            time_to_str(delivery_at),
            time_spend,
        )

        return time_spend

    def expect_mouse_sequence(self, x, y, buttons):
        """Returns the expected evdev sequence for a simple mouse event."""
        if buttons == 0:
            return [(0x3, 0x03A, 00000000), (0x03, 0x39, 0xFFFFFFFF), (0, 0, 0)]
        else:
            return [
                (0x3, 0x35, self.scale_axis(x, 0, self.width)),
                (0x3, 0x36, self.scale_axis(y, 0, self.height)),
                (0, 0, 0),
            ]
