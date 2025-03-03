import asyncio
import logging
import os
import platform
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest
import requests

from emu.process.command import Command
from emu.application import AnimationApplication
from emu.emulator_exceptions import EmulatorNotFoundException, EmulatorFailedToDownload
from emu.timing import eventually
from tests.test_utils import check_boot_from_snapshot

# This will run the tests in this module using this
# user configuration. This will fetch an image with api 33 and
# tag.id "google_apis"
#
# On M1 this will resolve to:  system-images;android-33;google_apis;arm64-v8a                                           | 5            | Google APIs ARM 64 v8a System Image
# On X64 this will resolve to: system-images;android-33;google_apis;x86_64
# avd_config = {"api": "33", "tag.id": "google_apis"}


def get_repository_url():
    return "https://dl.google.com/android/repository"


def get_emulator_filename(build_id):
    """given a build id, return the url and the path to download to"""

    if platform.system() == "Windows":
        return f"emulator-windows_x64-{build_id}.zip"
    elif platform.system() == "Linux":
        return f"emulator-linux_x64-{build_id}.zip"
    elif platform.system() == "Darwin":
        if platform.machine() == "arm64":
            return f"emulator-darwin_aarch64-{build_id}.zip"
        else:
            return f"emulator-darwin_x64-{build_id}.zip"


async def download_file(save_to_path, url):
    """Download the url to the path, skip if already done so"""
    if os.path.exists(save_to_path):
        logging.info("file %s exists, skip downloading", save_to_path)
        return
    logging.info("downloading file %s ...", save_to_path)
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        with open(save_to_path, "wb") as fd:
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    fd.write(chunk)
    except requests.exceptions.RequestException as e:
        logging.error(f"Download failed: %s", e)
        raise EmulatorFailedToDownload(e)


def extract_file(zf, info, extract_dir):
    zf.extract(info.filename, path=extract_dir)
    out_path = os.path.join(extract_dir, info.filename)

    perm = info.external_attr >> 16
    os.chmod(out_path, perm)


def unzip_file(path_to_zip_file):
    """Unziping the zip in the same directory"""
    directory_to_extract_to = path_to_zip_file.parent.absolute()
    with ZipFile(path_to_zip_file, "r") as zf:
        for info in zf.infolist():
            extract_file(zf, info, directory_to_extract_to)


def check_emulator_binaries(path_to_emulator_dir: Path) -> bool:
    """check emulator, qemu-system etc exists"""

    myemuexe = "emulator"
    if platform.system() == "Windows":
        myemuexe += ".exe"
    return (path_to_emulator_dir / myemuexe).exists()


async def download_emulator_zip(build_id: str) -> Path:
    """Downloads and extracts an emulator zip for the given build ID.

    If the emulator is already present in the Android SDK, it returns the path
    to the emulator binary. Otherwise, it downloads the zip file from the
    official repository, extracts it, and returns the path to the binary.

    Args:
        build_id: The build ID of the emulator to download.

    Returns:
        The path to the emulator executable.

    Raises:
        EmulatorNotFoundException: If the emulator cannot be downloaded or extracted.
        EmulatorFailedToDownload: If the emulator download fails.
    """
    sdk_path = Path(os.environ["ANDROID_SDK_ROOT"])
    emulator_dir = sdk_path / "emulators" / build_id / "emulator"
    emulator_exe = emulator_dir / "emulator"

    if check_emulator_binaries(emulator_dir):
        return emulator_exe.absolute()

    zip_filename = get_emulator_filename(build_id)
    remote_url = get_repository_url() + "/" + zip_filename
    local_zip_path = emulator_dir.parent / zip_filename

    emulator_dir.parent.mkdir(parents=True, exist_ok=True)

    try:
        await download_file(local_zip_path, remote_url)
    except EmulatorFailedToDownload as e:
        raise  # Re-raise the download exception

    if not local_zip_path.exists():
        raise EmulatorNotFoundException(f"Failed to download {remote_url}")

    unzip_file(local_zip_path)

    if not check_emulator_binaries(emulator_dir):
        raise EmulatorNotFoundException("Emulator binary not found after extraction.")

    return emulator_exe.absolute()


@pytest.mark.snapshot
@pytest.mark.flaky(reruns=0)
@pytest.mark.skip(reason="b375280350, no longer supported")
@pytest.mark.async_timeout(510)
async def test_can_load_oldsnapshot(emulator, pytestconfig):
    """test that current emulator can load the snapshot created by old emulator

    First, use old emulator to create a snapshot
    Second, load it with current emulator, make sure snapshot load is successful
    """
    await emulator.stop()
    assert not emulator.is_alive()

    # save tot exe
    totexe = emulator.exe

    # create snapshot with old emulator
    oldexe = await download_emulator_zip("11518282")
    logging.info("old emu: %s", oldexe)
    emulator.exe = oldexe
    myflags = ["-no-snapshot-load"]
    if platform.processor() == "i386" and platform.system() == "Darwin":
        myflags.append("-no-window")
    assert await emulator.launch(flags=myflags)

    # 99 percentile boots in less than 2 minutes.
    # go/stats/#report_id=Emulator%2FBootTime%2F7-day%20BootTime
    assert await emulator.wait_for_boot(timeout=120)

    apk = AnimationApplication(emulator)
    await apk.install()
    await apk.start()
    await emulator.stop()

    # Now we wait until the emulator has stopped.
    assert eventually(lambda: not emulator.is_alive(), timeout=20)

    # launch with tot
    emulator.exe = totexe
    assert await emulator.launch(flags=["-no-snapshot-save"])
    assert await emulator.wait_for_boot(timeout=120)

    def check_has_booted():
        return check_boot_from_snapshot(emulator.configuration.directory)

    assert await eventually(check_has_booted)


@pytest.mark.skipos("all", "Flaky and not needed for now.")
async def test_snapshot_download(emulator):
    """Make sure the emulator status is set to booted."""

    logging.info("Using %s", emulator)
    # Make sure this emulator is not running. Other tests might have been
    # using the same emulator.
    await emulator.stop()

    # The emulator is not running any more..
    assert not emulator.is_alive()

    # Emulator is now in a ready to go state with a default avd_config, but it is not yet
    # running
    config = emulator.configuration

    # Inspect the hardware
    assert config.hardware["hw.keyboard"] == "yes"

    # Get the path
    assert config.directory.exists()

    # We now actually launch the emulator from a clean slate.
    assert await emulator.launch(flags=["-wipe-data"])

    # The emulator kicks of its boot process, this should succeed
    assert await emulator.wait_for_boot(timeout=120)

    # Stops the emulator.
    await emulator.stop()

    # We should have created a default snapshot.
    assert (config.directory / "snapshots" / "default_boot").exists()
    assert (config.directory / "snapshots" / "default_boot" / "ram.bin").exists()
    assert (config.directory / "snapshots" / "default_boot" / "hardware.ini").exists()

    # Download the actual snapshot..
    # Note, this is currently fails..
    with pytest.raises(Exception):
        r = requests.get("https://my_downloadable_snapshot/ram.bin", stream=True)
        with open(
            config.directory / "snapshots" / "default_boot" / "ram.bin", "wb"
        ) as fd:
            for chunk in r.iter_content(chunk_size=4096):
                fd.write(chunk)

    # We now actually launch the emulator, without erasing it,
    assert await emulator.launch()

    # The emulator kicks of its boot process, this should succeed
    assert await emulator.wait_for_boot(timeout=120)
