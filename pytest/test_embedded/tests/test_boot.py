# Copyright 2023 The Android Open Source Project
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
import asyncio
import json
import logging
import platform
import re
import subprocess
import tempfile
from pathlib import Path

import psutil
import pytest
from aemu.proto.emulator_controller_pb2_grpc import EmulatorControllerStub
from google.protobuf import empty_pb2

from emu.emulator import Emulator
from emu.emulator_exceptions import EmulatorException, EmulatorDiedException
from emu.timing import eventually
from tests.test_utils import check_boot_from_snapshot


async def has_network(adb):
    """Checks if the emulator has a network connection.

    Verifies network connectivity by checking for the presence of either 'eth0'
    or 'wlan0' interfaces using the `ifconfig` command.

    Note: Tablets usually do not have eth0, whereas most others will have both.

    Args:
        adb: The adb connection object for the emulator.

    Returns:
        True if either 'eth0' or 'wlan0' interface is found, indicating
        a network connection; False otherwise.
    """
    result = await adb.shell("ifconfig")
    if "eth0" in result or "wlan0" in result:
        logging.info("Success: Network interfaces found. Result: %s", result)
        return True
    return False


def cpu_usage(emulator):
    """Checks the CPU usage of the emulator.

    Retrieves the CPU usage of the emulator process over a 2-second interval.

    Args:
        emulator: The Emulator object representing the running emulator.

    Returns:
        The CPU usage of the emulator process as a percentage.
    """
    proc_emu = psutil.Process(emulator.description.pid())
    cpu_usage = proc_emu.cpu_percent(interval=2)
    logging.info("Emulator usage is %d", cpu_usage)
    return cpu_usage


async def shutdown(emulator):
    """Shuts down the emulator gracefully.

    Attempts to shut down the emulator by sending a 'kill' command, allowing
    it to save a snapshot if applicable.  Waits for the emulator to fully
    shut down. If the initial shutdown attempt fails, a forced stop is
    attempted.

    Args:
        emulator: The Emulator object representing the running emulator.

    Raises:
        AssertionError: If the emulator fails to shut down.
    """
    await emulator.adb.run(["emu", "kill"])
    # For Windows, add a delay to ensure complete shutdown and avoid
    # potential multiinstance.lock issues.
    if platform.system() == "Windows":
        await asyncio.sleep(30)

    async def emulator_died():
        return not emulator.is_alive()

    await eventually(emulator_died, timeout=60)

    if emulator.is_alive():
        await emulator.stop(timeout=60)

    assert not emulator.is_alive()


async def get_booted_notification_time(emulator):
    """Retrieves the emulator boot time from the notification stream.

    Connects to the emulator's gRPC controller and listens for the 'booted'
    notification, which contains the boot time.

    Args:
        emulator: The Emulator object representing the running emulator.

    Returns:
        The boot time in milliseconds, or None if the notification is not received.
    """
    controller = EmulatorControllerStub(emulator.channel)
    stream = controller.streamNotification(empty_pb2.Empty())
    async for notification in stream:
        logging.info("Notification: %s", notification)
        if notification.HasField("booted"):
            logging.info("Boot completed in %d ms.", notification.booted.time)
            return notification.booted.time

    return None


@pytest.mark.boot
@pytest.mark.sanity
@pytest.mark.fast
@pytest.mark.wear
@pytest.mark.atv
@pytest.mark.tablet
@pytest.mark.async_timeout(180)
@pytest.mark.flaky(reruns=2, reruns_delay=2)
async def test_first_time_booted(emulator, record_property):
    """Make sure the emulator status is set to booted."""

    await emulator.stop()
    assert not emulator.is_alive()

    logging.info("Launching emulator from clean slate")
    myflags = ["-wipe-data", "-no-snapshot-load"]
    if platform.processor() == "i386" and platform.system() == "Darwin":
        myflags.append("-no-window")

    assert await emulator.launch(flags=myflags)

    logging.info("Wating for it to boot up ...")

    # This will throw an exception in case of a timeout, note that 99% of our
    # emulators launch in < 180 seconds.
    boot_time = await asyncio.wait_for(
        get_booted_notification_time(emulator), timeout=180
    )
    record_property("emulator_boot_time", boot_time)

    logging.info("Waiting for network.")

    async def network_up():
        return await has_network(emulator.adb)

    assert await eventually(network_up, timeout=30), "Eth0 or wlan are not up (yet?)!"
    await shutdown(emulator)


@pytest.mark.boot
@pytest.mark.sanity
@pytest.mark.async_timeout(120)
async def test_snapshot_booted(emulator):
    """Make sure the emulator status is able to boot from snapshot.

    It is important to boot fast from snapshot, that is why it
    is set to timeout in 60 seconds
    """
    await emulator.stop()
    assert not emulator.is_alive()

    logging.info("Launching emulator ...")
    myflags = ["-no-snapshot-save"]
    if platform.system() == "Windows":
        myflags.append("-read-only")

    assert await emulator.launch(flags=myflags)

    mytimeout = 120
    if platform.processor() == "i386" and platform.system() == "Darwin":
        mytimeout = 360
    logging.info("Wating for it to boot up from snapshot ...")
    assert await emulator.wait_for_boot(timeout=mytimeout)
    logging.info("Wating for it to stablize ...")

    # Ensure the emulator has snapshots available.
    console = await emulator.console()
    output = await console.send("avd snapshot list")
    if 'There is no snapshot available.' in output:
        raise EmulatorException("No snapshots found for the current AVD.")

    def has_booted_from_snapshot():
        return check_boot_from_snapshot(emulator.configuration.directory)

    assert await eventually(
        has_booted_from_snapshot
    ), f"The file {emulator.configuration.directory} does not exist or contain load_succeeded"

    await shutdown(emulator)


@pytest.mark.boot
@pytest.mark.skipos("win", "will turn on later")
@pytest.mark.flaky(reruns=0)  # b/286570480
@pytest.mark.async_timeout(400)
async def test_emulator_should_idle(emulator):
    """check emulator use less than 25% single cpu when idle."""

    await emulator.stop()
    assert not emulator.is_alive()

    logging.info("Launching emulator ...")
    myflags = ["-no-snapshot-save"]
    if platform.system() == "Windows":
        myflags.append("-read-only")

    assert await emulator.launch(flags=myflags)

    mytimeout = 45
    if platform.processor() == "i386" and platform.system() == "Darwin":
        mytimeout = 120
    logging.info(
        "Waiting at most %s seconds for emulator to boot from snapshot", mytimeout
    )
    assert await emulator.wait_for_boot(timeout=mytimeout)
    logging.info("Wating for it to stablize ...")

    def emulator_is_stable():
        """True if the emulator is stable, consuming less than 25% of the cpu."""
        return cpu_usage(emulator) <= 25

    assert await eventually(
        emulator_is_stable, timeout=300
    ), f"Cpu did not stabilize (i.e. cpu usage < 25%), cpu: {cpu_usage(emulator)}"

    logging.info("Shutting it down ...")
    if emulator.is_alive():
        await emulator.stop()
    logging.info("emulator is shut down successfully")


@pytest.mark.boot
async def test_a_booted_emulator_immediately_notifies_it_has_booted(avd):
    assert await avd.has_booted()
    assert await asyncio.wait_for(get_booted_notification_time(avd), timeout=10)


@pytest.mark.slow
@pytest.mark.boot
@pytest.mark.fast
@pytest.mark.async_timeout(180)
@pytest.mark.flaky(reruns=0)
async def test_emulator_debug_startup(avd):
    """Ensure the emulator is able to launch with DEBUG messages.

    Args:
        avd (BaseEmulator): Fixture that gives access to a booted emulator.

    Test UUID: a5fb9248-8bc8-43b2-ae22-22594b7888ad

    Test steps:
        1. From a subprocess run: emulator -help-debug-tags" (Verify 1).
        2. From a subprocess run: emulator -debug all (Verify 2).

    Verify:
        1. A list of available debug tags are displayed.
        2. The emulator launches with debug messages (observed from a stdout file).
    """
    # Check if the emulator binary prints the debug tags.
    cmd = " ".join((str(avd.exe), "-help-debug-tags"))
    try:
        output = subprocess.check_output(cmd, shell=True)
        assert "-debug" in output.decode(), "Emulator debug flags not found"
    except subprocess.CalledProcessError as e:
        raise AssertionError(f"Command '{' '.join(cmd)}' failed with error: {e.output}")

    # Check if the emulator output contains debug messages.

    logging.info("Launching emulator with option 'debug -all' ...")

    # Sample debug message format: 07:53:41.641776 112835 DEBUG filename.
    # Debug logs from main-emulator.cpp always appear as they come before the debug flag
    # is parsed so should not be counted.
    debug_pattern = r"^\d{2}:\d{2}:\d{2}\.\d{6} \d+ DEBUG\s+((?!main-emulator\.cpp).)*$"

    # Redirect the emulator stdout/stderr to a temporary file.
    with tempfile.NamedTemporaryFile() as emu_output:
        flags = [
            "-debug",
            "all",
            "-stdouterr-file",
            emu_output.name,
            "-no-snapshot-save",
        ]

        await avd.restart(flags)
        await asyncio.sleep(5)

        contents = emu_output.read().decode()
        has_debug_messages = re.search(debug_pattern, contents, re.MULTILINE)
        assert has_debug_messages, "DEBUG messages not found in the emulator output"
        logging.info(f"Found the debug message '{has_debug_messages.group()}'")


@pytest.mark.oldapiboot
@pytest.mark.async_timeout(200)
async def test_first_time_booted_old_api(emulator):
    """Make sure the emulator status is set to booted."""

    await emulator.stop()
    logging.info("Launching emulator ...")
    myflags = ["-wipe-data"]
    if platform.processor() == "i386" and platform.system() == "Darwin":
        myflags.append("-no-window")

    assert await emulator.launch(flags=myflags)

    logging.info("Waiting for it to boot up ...")
    # 99 percentile boots in less than 2 minutes.
    await asyncio.wait_for(get_booted_notification_time(emulator), timeout=180)

    logging.info("Shutting down the emulator ...")
    if emulator.is_alive():
        await emulator.stop()
    logging.info("emulator is shut down successfully")


@pytest.mark.fast
@pytest.mark.async_timeout(240)
@pytest.mark.parametrize("core", [1, 2])
async def test_multicore_startup(emulator, core):
    """Verify emulator launches without issues on single and dual core CPUs."""

    # Launch the emulator with the specificed multicore configuration.
    myflags = ["-cores", core]
    logging.info(f"Launching emulator with {core} core ...")

    await emulator.restart(emu_flags=myflags)
    # 99 percentile boots in less than 2 minutes.
    # go/stats/#report_id=Emulator%2FBootTime%2F7-day%20BootTime
    assert await emulator.wait_for_boot(
        timeout=120
    ), f"The emulator couldn't be launched with {core} core"
    await emulator.stop()


@pytest.mark.fast
@pytest.mark.async_timeout(240)
async def test_boot_without_internet(emulator):
    """Verify emulator can boot with no internet.

    Args:
        emulator (BaseEmulator): Fixture that gives access to a configured emulator.

    Notes:
        To disable internet access at boot time, the 'restrict=on' option
        is added to the wifi and radio (user mode) network settings.
        This causes the emulator to be isolated, not being able to contact
        the host. No IP packages should be routed over the host to the outside.
    """
    my_flags = [
        "-wifi-user-mode-options",
        "restrict=on",
        "-network-user-mode-options",
        "restrict=on",
    ]

    # Launch the emulator.
    await emulator.restart(emulator.launch_flags + my_flags)
    # 99 percentile boots in less than 2 minutes.
    # go/stats/#report_id=Emulator%2FBootTime%2F7-day%20BootTime
    assert await emulator.wait_for_boot(
        timeout=120
    ), f"The emulator wasn't able to boot without internet."

    # Make sure the emulator launched without internet access.
    async def emulator_has_no_internet_access(emulator):
        result = await emulator.adb.shell("ping -c 3 www.google.com")
        for line in result.rstrip().splitlines():
            if "64 bytes from" in line and "icmp_seq" in line and "ttl" in line:
                return False
        return True

    assert await emulator_has_no_internet_access(
        emulator
    ), "The emulator was launched with internet access."


@pytest.mark.fast
@pytest.mark.async_timeout(120)
async def test_gpu_emulation(emulator):
    debug_pattern = "hw.gpu.enabled = true"
    # Redirect the emulator stdout/stderr to a temporary file.
    with tempfile.NamedTemporaryFile() as emu_output:
        flags = ["-gpu", "on", "-verbose", "-stdouterr-file", emu_output.name]

        await emulator.restart(flags)
        await asyncio.sleep(5)
        emu_output.seek(0)
        if not emulator.is_alive():
            raise EmulatorDiedException("Emulator is no longer alive")

        contents = emu_output.read().decode()
        if not contents:
            raise ValueError("If is empty")
        has_debug_messages = re.search(debug_pattern, contents)
        assert has_debug_messages, "DEBUG messages not found in the emulator output"
        logging.info("Found the debug message '%s'", has_debug_messages.group())


@pytest.mark.fast
@pytest.mark.async_timeout(120)
async def test_gpu_host_emulation(emulator):
    debug_pattern = "hw.gpu.mode = host"
    # Redirect the emulator stdout/stderr to a temporary file.
    with tempfile.NamedTemporaryFile() as emu_output:
        flags = ["-gpu", "host", "-verbose", "-stdouterr-file", emu_output.name]

        await emulator.restart(flags)
        await asyncio.sleep(5)
        emu_output.seek(0)
        if not emulator.is_alive():
            raise EmulatorDiedException("Emulator is no longer alive")

        contents = emu_output.read().decode()
        if not contents:
            raise ValueError("If is empty")
        has_debug_messages = re.search(debug_pattern, contents)
        assert has_debug_messages, "DEBUG messages not found in the emulator output"
        logging.info("Found the debug message '%s'", has_debug_messages.group())
