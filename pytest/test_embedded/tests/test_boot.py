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
import logging
import platform
import time
from pathlib import Path

import psutil
import pytest
from google.protobuf import empty_pb2
from aemu.proto.emulator_controller_pb2 import BootCompletedNotication

from emu.apk import APP_DEBUG_APK
from emu.timing import eventually

# This will run the tests in this module using this
# user configuration. This will fetch an image with api 33 and
# tag.id "google_apis"
#
# On M1 this will resolve to:  system-images;android-33;google_apis;arm64-v8a                                           | 5            | Google APIs ARM 64 v8a System Image
# On X64 this will resolve to: system-images;android-33;google_apis;x86_64
# avd_config = {"api": "33", "tag.id": "google_apis"}


def has_network(adb):
    """check whether it has network or not
    adb shell ifconfig, it should have both eth0 and wlan0
    """
    radio_wifi = False
    result = adb.shell("ifconfig")
    if "eth0" in result and "wlan0" in result:
        logging.info("success result %s", result)
        radio_wifi = True
    return radio_wifi


def cpu_usage(emulator):
    """
    Check if the CPU usage of the specified emulator is less than a threshold.

    This function checks the CPU usage of an emulator and compares it to the given threshold (25%).
    If the CPU usage is lower than or equal to the threshold, the function returns True;
    otherwise, it returns False."""
    proc_emu = psutil.Process(emulator.description.pid())
    cpu_usage = proc_emu.cpu_percent(interval=2)
    logging.info("emulator usage is %d", cpu_usage)
    return cpu_usage


def shutdown(emulator):
    # kill is the way to ask it to save snapshot if applicable and quit
    emulator.adb.run(["emu", "kill"])
    # for windows, wait 30 seconds for it to fully shutdown to avoid
    # the multiinstnace.lock failure, hopefully, especially on gcp windows
    if platform.system() == "Windows":
        time.sleep(30)

    def emulator_died():
        return not emulator.is_alive()

    eventually(emulator_died, timeout=60)

    # Maybe we didn't shutdown in time, if so try some other method.
    if emulator.is_alive():
        emulator.stop(timeout=60)

    assert not emulator.is_alive()


def check_has_booted_notification(emulator, timeout):
    response_iterator = (
        emulator.description.get_emulator_controller().streamNotification(
            empty_pb2.Empty(), timeout=timeout
        )
    )

    for notification in response_iterator:
        logging.info("Notification: %s", notification)
        if notification.HasField("booted"):
            logging.info("Boot completed in %d ms.", notification.booted.time)
            return True

    return False


@pytest.mark.boot
@pytest.mark.e2e
@pytest.mark.sanity
@pytest.mark.fast
@pytest.mark.timeout(timeout=2800, func_only=True)
def test_first_time_booted(emulator):
    """Make sure the emulator status is set to booted."""

    emulator.stop()
    logging.info("Launching emulator ...")
    myflags = ["-wipe-data", "-no-snapshot-load"]
    if platform.processor() == "i386" and platform.system() == "Darwin":
        myflags.append("-no-window")

    assert emulator.launch(flags=myflags)

    logging.info("Wating for it to boot up ...")

    assert check_has_booted_notification(emulator, timeout=1080)

    logging.info("Wating for it to stablize ...")

    def network_up():
        return has_network(emulator.adb)

    # make sure it has both radio and wifi
    assert eventually(network_up, timeout=30), "Radio and wifi are not ready!"
    assert emulator.install_apk(APP_DEBUG_APK.absolute(), "com.google.AnimateBox")

    shutdown(emulator)


def check_boot_from_snapshot(avdpath) -> bool:
    mypath = Path(avdpath, "snapshot.trace")
    with open(mypath) as fp:
        for line in fp:
            line.rstrip()
            logging.info("reading line '%s'", line)
            if "load_succeeded" in line:
                return True

    return False


@pytest.mark.boot
@pytest.mark.e2e
@pytest.mark.sanity
@pytest.mark.timeout(timeout=60, func_only=True)
@pytest.mark.timeout_win(timeout=120)
def test_snapshot_booted(emulator):
    """Make sure the emulator status is able to boot from snapshot.

    It is important to boot fast from snapshot, that is why it
    is set to timeout in 60 seconds
    """

    emulator.stop()
    logging.info("Launching emulator ...")
    myflags = ["-no-snapshot-save"]
    if platform.system() == "Windows":
        myflags.append("-read-only")

    assert emulator.launch(flags=myflags)

    mytimeout = 45
    if platform.processor() == "i386" and platform.system() == "Darwin":
        mytimeout = 360
    logging.info("Wating for it to boot up from snapshot ...")
    assert emulator.wait_for_boot(timeout=mytimeout)
    logging.info("Wating for it to stablize ...")

    def has_booted_from_snapshot():
        return check_boot_from_snapshot(emulator.configuration.directory)

    assert eventually(
        has_booted_from_snapshot
    ), f"The file {emulator.configuration.directory} does not exist or contain load_succeeded"

    shutdown(emulator)


@pytest.mark.boot
@pytest.mark.e2e
@pytest.mark.timeout(timeout=600, func_only=True)
@pytest.mark.skipos('win', 'will turn on later')
@pytest.mark.flaky(reruns=3, reruns_delay=5)  # b/286570480
def test_emulator_should_idle(emulator):
    """check emulator use less than 25% single cpu when idle."""

    emulator.stop()
    logging.info("Launching emulator ...")
    myflags = ["-no-snapshot-save"]
    if platform.system() == "Windows":
        myflags.append("-read-only")

    assert emulator.launch(flags=myflags)

    mytimeout = 45
    if platform.processor() == "i386" and platform.system() == "Darwin":
        mytimeout = 360
    logging.info(
        "Waiting at most %s seconds for emulator to boot from snapshot", mytimeout
    )
    assert emulator.wait_for_boot(timeout=mytimeout)
    logging.info("Wating for it to stablize ...")

    def emulator_is_stable():
        """True if the emulator is stable, consuming less than 25% of the cpu."""
        return cpu_usage(emulator) <= 25

    assert eventually(
        emulator_is_stable, timeout=300
    ), f"Cpu did not stabilize (i.e. cpu usage < 25%), cpu: {cpu_usage(emulator)}"

    logging.info("Shutting it down ...")
    if emulator.is_alive():
        emulator.stop(timeout=60)
    logging.info("emulator is shut down successfully")



@pytest.mark.boot
@pytest.mark.e2e
@pytest.mark.timeout(timeout=10, func_only=True)
@pytest.mark.timeout_win(timeout=60)
def test_a_booted_emulator_immediately_notifies_it_has_booted(avd):
    assert avd.has_booted()
    assert check_has_booted_notification(avd, timeout=10)
