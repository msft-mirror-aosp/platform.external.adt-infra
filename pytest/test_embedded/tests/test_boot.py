import logging
import platform
import psutil
import pytest
import sys
import time
from pathlib import Path
from google.protobuf import empty_pb2
from emu.apk import APP_DEBUG_APK

# This will run the tests in this module using this
# user configuration. This will fetch an image with api 33 and
# tag.id "google_apis"
#
# On M1 this will resolve to:  system-images;android-33;google_apis;arm64-v8a                                           | 5            | Google APIs ARM 64 v8a System Image
# On X64 this will resolve to: system-images;android-33;google_apis;x86_64
# avd_config = {"api": "33", "tag.id": "google_apis"}


def has_network(adb):
    """check whether it has network or not
    adb shell ifconfig, it shouls have both eth0 and wlan0
    """
    radio_wifi = False
    result = adb.shell("ifconfig")
    if "eth0" in result and "wlan0" in result:
        logging.info("success result %s", result)
        radio_wifi = True
    return radio_wifi


def check_cpu_usage_less_than_threshold(emulator):
    proc_emu = psutil.Process(emulator.description.pid())
    cpu_usage = proc_emu.cpu_percent(interval=2)
    logging.info("emulator usage is %d", cpu_usage)
    if cpu_usage <= 25:
        return True
    return False


def shutdown(emulator):
    # kill is the way to ask it to save snapshot if applicable and quit
    emulator.adb.run(["emu", "kill"])
    # for windows, wait 30 seconds for it to fully shutdown to avoid
    # the multiinstnace.lock failure, hopefully, especially on gcp windows
    if platform.system() == "Windows":
        time.sleep(30)
    count = 0
    while count < 60:
        time.sleep(1)
        count += 1
        if not emulator.is_alive():
            break
    if emulator.is_alive():
        emulator.stop(timeout=60)
    assert not emulator.is_alive()


@pytest.mark.boot
@pytest.mark.e2e
@pytest.mark.flaky(reruns=3, reruns_delay=5)
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
    assert emulator.wait_for_boot(timeout=1080)
    logging.info("Wating for it to stablize ...")
    # make sure it has both radio and wifi
    count = 0
    while count < 30:
        time.sleep(1)
        count += 1
        if has_network(emulator.adb):
            logging.info("found radio and wifi")
            break
        logging.info("radio or wifi not ready yet")

    assert emulator.install_apk(APP_DEBUG_APK.absolute(), "com.google.AnimateBox")

    logging.info("Shutting it down ...")
    shutdown(emulator)
    logging.info("emulator is shut down successfully")


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
@pytest.mark.timeout(timeout=60, func_only=True)
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
    count = 0
    while count < 10:
        time.sleep(1)
        count += 1
        if check_boot_from_snapshot(emulator.configuration.directory):
            break

    assert check_boot_from_snapshot(emulator.configuration.directory)
    logging.info("Shutting it down ...")
    shutdown(emulator)
    logging.info("emulator is shut down successfully")


@pytest.mark.boot
@pytest.mark.e2e
@pytest.mark.timeout(timeout=600, func_only=True)
@pytest.mark.skipif(sys.platform == "win32", reason="will turn on later")
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
    logging.info("Wating for it to boot up from snapshot ...")
    assert emulator.wait_for_boot(timeout=mytimeout)
    logging.info("Wating for it to stablize ...")
    count = 0
    while count < 100:
        time.sleep(1)
        count += 1
        if check_cpu_usage_less_than_threshold(emulator):
            break

    # cannot keep cpu spinning
    assert count < 100
    logging.info("Shutting it down ...")
    if emulator.is_alive():
        emulator.stop(timeout=60)
    logging.info("emulator is shut down successfully")
