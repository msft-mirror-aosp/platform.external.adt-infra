# Copyright 2020 - The Android Open Source Project
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
"""A basic emulator launcher."""
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterator, Optional

from emu.template_writer import TemplateWriter


class AndroidAvdHomeDoesNotExist(Exception):
    pass


class SystemImageDirectoryDoesNotExist(Exception):
    pass


class SystemImageDownloadFailed(Exception):
    pass


class SdkManagerDoesNotExist(Exception):
    pass


class UnsupportedAbiOrCpu(Exception):
    pass


class SystemImages(object):

    IMAGE = re.compile(
        r".*android-(\d+)[\/\\](default|google_apis|google_apis_playstore|android-tv)[\/\\](x86|x86_64|arm64-v8a)[\/\\]system.img$"
    )

    def __init__(self, sdk_root: Path = Path(os.environ.get("ANDROID_SDK_ROOT", "."))):
        """A Class that can be used to discover and install system images

        Args:
            sdk_root (Path, optional): The sdk root to use. Defaults to "$ANDROID_SDK_ROOT" environment.

        Raises:
            SystemImageDirectoryDoesNotExist: If no system-images directory was find under the root
            SdkManagerDoesNotExist: If the sdk manager executable was not found in the sdk root
        """
        abs_root = Path(sdk_root).absolute()
        self.sys_root = abs_root / "system-images"

        if not self.sys_root.exists():
            raise SystemImageDirectoryDoesNotExist(
                f"The directory {self.sys_root} does not exist. Is ANDROID_SDK_ROOT set properly?"
            )

        self.sdk_manager = shutil.which(
            abs_root / "cmdline-tools" / "latest" / "bin" / "sdkmanager"
        )
        if not self.sdk_manager:
            raise SdkManagerDoesNotExist(
                f"The sdk manager was not found in {self.sys_root}. Is ANDROID_SDK_ROOT set properly?"
            )

    def available(self) -> Iterator[dict[str, str]]:
        """An iterator over all available system images

        Yields:
            Iterator[dict[str, str]]: A dictionary with api, tag, abi, and cpu.
        """
        logging.info("Looking for images in %s", self.sys_root)
        for x in self._recursive_iglob(self.sys_root):
            logging.debug("Considering %s", x)
            m = self.IMAGE.match(str(x))
            if m:
                yield {
                    "api": m.group(1),
                    "tag": m.group(2),
                    "abi": m.group(3),
                    "cpu": m.group(3),
                    "image_dir": os.path.join(
                        "system-images",
                        "android-{}".format(m.group(1)),
                        m.group(2),
                        m.group(3),
                    ),
                }

    def find(self, api: str, abi: str, tag: str) -> Optional[dict[str, str]]:
        """Finds the system image with the given api, abi and tag.

        Args:
            api (str): Api level, usually a number, or first letter of desert
            abi (str): The abi of interest, one of x86|x86_64|arm64-v8a
            tag (str): Tag of interest, one of default|google_apis|google_apis_playstore|android-tv

        Returns:
            Optional[dict[str, str]]:  A dictionary with api, tag, abi, and cpu.
        """
        return next(
            (
                x
                for x in self.available()
                if x["api"] == api and x["abi"] == abi and x["tag"] == tag
            ),
            None,
        )

    def install(self, api: str, abi: str, tag: str = "google_apis") -> dict[str, str]:
        """Installs the system image with the given api, abi and tag.

        Args:
            api (str): Api level, usually a number, or first letter of desert
            abi (str): The abi of interest, one of x86|x86_64|arm64-v8a
            tag (str): Tag of interest, one of default|google_apis|google_apis_playstore|android-tv

        Raises:
            SystemImageDownloadFailed: If we failed to obtain the given image

        Returns:
            dict[str, str]:  A dictionary with api, tag, abi, and cpu.
        """
        logging.info("Installing system-images;android-{};{};{}".format(api, tag, abi))
        donwload = subprocess.run(
            [
                self.sdk_manager,
                "system-images;android-{};{};{}".format(api, tag, abi),
            ],
            stderr=subprocess.PIPE,
        )
        if donwload.returncode != 0:
            logging.error("sdkmanager: %s", donwload.stderr.decode("UTF-8"))
            raise SystemImageDownloadFailed(
                f"Failed to obtain image for {api}-{abi}-{tag}"
            )
        return self.find(api, abi, tag)

    def _recursive_iglob(self, rootdir: Path) -> Iterator[Path]:
        """Recursively glob the directory for files.

        Args:
            rootdir (Path): Root directory to start searching

        Yields:
            Iterator[Path]: Discovered filename
        """
        for root, _, filenames in os.walk(rootdir):
            for filename in filenames:
                fname = Path(root) / filename
                yield fname


class AvdWriter(object):

    # map from cpu --> abi.
    CPU_TO_ABI = {
        "arm64-v8a": "arm64-v8a",
        "arm64": "arm64-v8a",
        "i386": "x86",
        "x86": "x86",
        "x86_64": "x86_64",
    }

    # Set of ABI's that we have system images for
    SUPPORTED_ABI = ["arm64-v8a", "x86", "x86_64"]

    def __init__(
        self,
        sdk_root: Path = Path(os.environ.get("ANDROID_SDK_ROOT", ".")),
        avd_home: Path = Path(
            os.environ.get("ANDROID_AVD_HOME") or Path.home() / ".android" / "avd"
        ),
    ):
        """An AvdWriter can be used to dynamically create avds of a given abi, tag and api level

        The AvdWriter uses a Pixel-2 device as a template and will obtain the required system images
        if they are not available.

        The AVDs will be created in the avd_home directory, and system-images will be placed in the
        sdk_root.

        Args:
            sdk_root (Path, optional): The sdk root to use. Defaults to "$ANDROID_SDK_ROOT" environment.
            avd_home (Path, optional): The sdk root to use. Defaults to "$ANDROID_AVD_HOME" environment, or ~/.android/avd.

        Raises:
            AndroidAvdHomeDoesNotExist: If the avd_home does not exist.
            SystemImageDirectoryDoesNotExist: If no system-images directory was find under the root
            SdkManagerDoesNotExist: If the sdk manager executable was not found in the sdk root
        """
        if not Path(avd_home).exists():
            raise AndroidAvdHomeDoesNotExist(
                f"The directory {avd_home} directory does not exist Is ANDROID_AVD_HOME set properly?"
            )

        self.avd_home = Path(avd_home).absolute()
        self.sys_imgs = SystemImages(sdk_root)
        self.writer = TemplateWriter(self.avd_home)

    def _write_config_ini(
        self, name: str, avd: str, custom_cfg: dict[str, str]
    ) -> None:
        """Writes the custom config ini to the avd_home directory"""
        cfg = self.writer.template_to_dict("Pixel2.avd/config.ini", avd)
        cfg.update(custom_cfg)

        cfg_file = f"{name}.avd/config.ini"
        dest = self.avd_home / cfg_file
        logging.info("Writing confing ini to %s", dest)
        if not dest.parent.exists():
            os.makedirs(dest.parent)

        with open(dest, "w") as f:
            for k, v in cfg.items():
                f.write(f"{k} = {v}\n")

    def _create_avd(
        self, api: str, abi: str, tag: str, name: str, custom_cfg: dict[str, str]
    ) -> None:
        avd = self.sys_imgs.find(api, abi, tag)
        if not avd:
            avd = self.sys_imgs.install(api, abi, tag)
        avd["name"] = name
        avd["avd_home"] = self.avd_home

        self.writer.write_template("Pixel2.ini", avd, f"{name}.ini")
        self._write_config_ini(name, avd, custom_cfg)

    def create_from_config(self, config: dict[str, str]) -> str:
        """Create a basic avd using the given configuration

        The configuration should have the following entries:

            api (str): Api level, usually a number, or first letter of desert
            abi (str): The abi of the machine. Note that qemu must support this abi!
            tag (str): Tag of interest, one of default|google_apis|google_apis_playstore|android-tv

        Note, you will need to look at the actual templates (templates/Pixel2.avd/config.ini) to see
        which values you can actually pass in as config.

        Args:
            config (dict[str, str]): _description_

        Returns:
            str: _description_
        """
        abi = config["abi"]
        tag = config["tag.id"]
        api = config["api"]

        if not abi in self.SUPPORTED_ABI:
            raise UnsupportedAbiOrCpu(
                f"Abi {abi} is not supported, please use one of: {', '.join(self.SUPPORTED_ABI)}"
            )

        name = "{}_{}_{}".format(api, tag, abi)
        avd_cfg = {
            "AvdId": name,
            "tag.id": tag,
            "abi.type": abi,
        }
        avd_cfg.update(config)

        self._create_avd(api, abi, tag, name, avd_cfg)
        return name

    def create(self, api: str, abi: str, tag: str = "google_apis") -> str:
        """Create a basic avd using the given api, abi and tag.

        The avd is based on a Pixel-2.

        Args:
            api (str): Api level, usually a number, or first letter of desert
            abi (str): The abi of interest, one of x86|x86_64|arm64-v8a
            tag (str): Tag of interest, one of default|google_apis|google_apis_playstore|android-tv

        Returns:
            str: The name of the avd that can be launched by the emulator.
        """
        return self.create_from_config({"abi": abi, "api": api, "tag.id": tag})
