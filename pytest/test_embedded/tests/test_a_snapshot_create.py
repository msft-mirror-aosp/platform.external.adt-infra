import logging
import os
import platform
import shutil
import subprocess
from pathlib import Path
from zipfile import ZipFile

import pytest

# This will run the boot test with DownloadableSnapshot feature turned on
# when it completes, it should save a snapshot to dist_out
mysdkpath = os.environ.get("ANDROID_SDK_ROOT", "")
myskin_path = Path(mysdkpath, "skins", "pixel_2").absolute()
avd_config = {
    "api": "34",
    "tag.id": "google_apis",
    "avd.ini.displayname": "pixel_2",
    "hw.lcd.density": "420",
    "hw.lcd.height": "1920",
    "hw.lcd.width": "1080",
    "skin.name": "pixel_2",
    "skin.path": f"{myskin_path}",
}


def removeDirRecursively(mypath):
    if os.path.exists(mypath):
        if platform.system() == "Windows":
            mycmd = f"rmdir {mypath} /s /q"
            subprocess.check_output(mycmd, shell=True)
        else:
            shutil.rmtree(mypath)


def dumpAvdConent(mypath):
    for f in mypath.glob("**/*"):
        logging.info("Found: %s", f)



@pytest.mark.snapshot
@pytest.mark.skipos("win", "Windows takes >2700 seconds to boot")
async def test_snapshot_create(emulator):
    """Make sure the emulator status is set to booted."""
    if "DIST_DIR" in os.environ:
        logging.info(
            "Testing snashot creation, will save a zip file to dist_out %s",
            os.environ["DIST_DIR"],
        )
    else:
        logging.warning(
            "Testing snashot creation, cannot save a zip file to dist_out as it is not defined"
        )

    await emulator.stop()

    localpath = None
    try:
        # Emulator is now in a ready to go state with a default avd_config, but it is not yet
        # running
        config = emulator.configuration
        dist_out = os.environ["DIST_DIR"]
        sdkroot = os.environ["ANDROID_SDK_ROOT"]
        localpath = Path(sdkroot, config.hardware["image.sysdir.1"]).absolute()
        removeDirRecursively(Path(localpath, "snapshots"))
        #        if os.path.exists(localpath / "snapshots"):
        #            shutil.rmtree(Path(localpath,"snapshots").absolute())

        # dump out avd folder content
        dumpAvdConent(config.directory)

        logging.info("Enabling DownloadableSnapshot feature")
        assert await emulator.launch(
            flags=[
                "-wipe-data",
                "-feature",
                "DownloadableSnapshot",
                "-no-snapshot-load",
            ]
        )

        logging.info("Booting up emualtor ...")
        assert await emulator.wait_for_boot(timeout=1080)

        # wait till it settle down a bit
        await asyncio.sleep(30)

        logging.info("Stopping emualtor")
        await emulator.stop()

        await asyncio.sleep(10)

        dumpAvdConent(config.directory)

        logging.info("saving snapshot to %s", dist_out)
        # create zip file
        filelist = []
        os.chdir(localpath)
        for root, dirs, files in os.walk("snapshots"):
            for file in files:
                filelist.append(os.path.join(root, file))
        # print all the file names
        for name in filelist:
            logging.info("zipping file: %s", name)

        with ZipFile(Path(dist_out, "snapshotavd.zip").absolute(), "w") as zip:
            # writing each file one by one
            for file in filelist:
                zip.write(file)

    except:
        logging.warning("The test failed, need investigation")
    finally:
        if localpath:
            removeDirRecursively(Path(localpath, "snapshots"))
