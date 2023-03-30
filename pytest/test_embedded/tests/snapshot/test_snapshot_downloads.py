import pytest
import requests
import logging
import platform
import os
import time
from pathlib import Path
from emu.process.command import Command

from zipfile import ZipFile

# This will run the tests in this module using this
# user configuration. This will fetch an image with api 33 and
# tag.id "google_apis"
#
# On M1 this will resolve to:  system-images;android-33;google_apis;arm64-v8a                                           | 5            | Google APIs ARM 64 v8a System Image
# On X64 this will resolve to: system-images;android-33;google_apis;x86_64
# avd_config = {"api": "33", "tag.id": "google_apis"}


def get_repository_url():
    return ("https://dl.google.com/android/repository")

def get_emulator_filename(build_id):
    """ given a build id, return the url and the path to download to

    """

    if platform.system() == "Windows":
            return f"emulator-windows_x64-{build_id}.zip"
    elif platform.system() == "Linux":
            return f"emulator-linux_x64-{build_id}.zip"
    elif platform.system() == "Darwin":
        if platform.machine() == "arm64":
            return f"emulator-darwin_aarch64-{build_id}.zip"
        else:
            return f"emulator-darwin_x64-{build_id}.zip"

def download_file(save_to_path, url):
    """ Download the url to the path, skip if already done so

    """
    if os.path.exists(save_to_path):
        logging.info("file %s exists, skip downloading", save_to_path)
        return
    logging.info("downloading file %s ...", save_to_path)
    cmd = Command(["curl", "-o", save_to_path, url])
    cmd.run_until_finished(timeout=500)
    return

    if True:
        r = requests.get(url, stream=True)
        with open(save_to_path) as fd:
            for chunk in r.iter_content(chunk_size=4096):
                fd.write(chunk)
def extract_file( zf, info, extract_dir ):
    zf.extract( info.filename, path=extract_dir )
    out_path = os.path.join( extract_dir, info.filename )

    perm = info.external_attr >> 16
    os.chmod( out_path, perm )

def unzip_file(path_to_zip_file):
    """ Unziping the zip in the same directory

    """
    directory_to_extract_to = path_to_zip_file.parent.absolute()
    with ZipFile(path_to_zip_file, 'r') as zf:
        for info in zf.infolist():
            extract_file( zf, info, directory_to_extract_to)

def check_emulator_binaries(path_to_emulator_dir) -> bool:
    """ check emulator, qemu-system etc exists
    """

    myemuexe = "emulator"
    if platform.system() == "Windows":
        myemuexe += ".exe"
    return os.path.exists(Path(path_to_emulator_dir, myemuexe))

def download_emulator_zip(build_id):
    """ Download an emulator zip with given build id

    """
    mysdkpath = os.environ["ANDROID_SDK_ROOT"]
    logging.info("sdk root %s", mysdkpath)
    mydownloaded_emulator_path = Path(mysdkpath, "emulators").absolute()
    logging.info("sdk emulator %s", mydownloaded_emulator_path)
    if check_emulator_binaries(Path(mydownloaded_emulator_path , f"{build_id}", "emulator")):
        return Path(mydownloaded_emulator_path , f"{build_id}", "emulator", "emulator").absolute()
    remote_long_path_name = get_repository_url() + "/" + get_emulator_filename(build_id)
    local_long_path_name = Path(mydownloaded_emulator_path,  f"{build_id}",  get_emulator_filename(build_id))
    Path(mydownloaded_emulator_path, f"{build_id}").mkdir(parents=True, exist_ok=True)
    logging.info("now download %s from %s", local_long_path_name, remote_long_path_name)
    download_file(local_long_path_name, remote_long_path_name)
    assert os.path.exists(local_long_path_name)
    if not check_emulator_binaries(Path(mydownloaded_emulator_path , f"{build_id}", "emulator")):
        unzip_file(local_long_path_name)
    assert check_emulator_binaries(Path(mydownloaded_emulator_path , f"{build_id}", "emulator"))
    return Path(mydownloaded_emulator_path , f"{build_id}", "emulator", "emulator").absolute()

def check_boot_from_snapshot(avdpath)->bool :
  mypath = Path(avdpath, "snapshot.trace")
  with open(mypath) as fp:
      for line in fp:
          line.rstrip()
          logging.info("reading line '%s'", line)
          if "load_succeeded" in line:
              return True

  return False

@pytest.mark.e2e
@pytest.mark.skipif(platform.system() == "Darwin" and platform.processor() == "i386" , reason="other platforms come later")
def test_can_load_oldsnapshot(emulator):
    """ test that current emulator can load the snapshot created by old emulator

        First, use old emulator to create a snapshot
        Second, load it with current emulator, make sure snapshot load is successful
    """

    emulator.stop()

    # save tot exe
    totexe = emulator.exe

    # create snapshot with old emulator
    oldexe = download_emulator_zip("9847722")
    logging.info("old emu: %s", oldexe)
    emulator.exe = oldexe;
    assert emulator.launch(flags=["-no-snapshot-load"])
    assert emulator.wait_for_boot(timeout=420)
    # there is no reliable way to detect it has reach home screen
    # so just wait enough long
    time.sleep(10)
    # windows need extra time  :(
    if platform.system() == "Windows":
        time.sleep(20)
    emulator.stop()
    # there is no reliable way to detect it has done saving
    # so just wait enough long
    time.sleep(10)

    # launch with tot
    emulator.exe = totexe
    assert emulator.launch(flags=["-no-snapshot-save"])
    assert emulator.wait_for_boot(timeout=60)

    count = 0
    while count < 10:
        time.sleep(1)
        count += 1
        if check_boot_from_snapshot(emulator.configuration.directory):
            break

    assert check_boot_from_snapshot(emulator.configuration.directory)

@pytest.mark.e2e
@pytest.mark.skip(reason="flaky and not needed for now")
@pytest.mark.timeout(timeout=600, func_only=True)
def test_snapshot_download(emulator):
    """Make sure the emulator status is set to booted."""

    logging.info("Using %s", emulator)
    # Make sure this emulator is not running. Other tests might have been
    # using the same emulator.
    emulator.stop()

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
    assert emulator.launch(flags=["-wipe-data"])

    # The emulator kicks of its boot process, this should succeed
    assert emulator.wait_for_boot(timeout=420)

    # Stops the emulator.
    emulator.stop()

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
    assert emulator.launch()

    # The emulator kicks of its boot process, this should succeed
    assert emulator.wait_for_boot(timeout=180)
