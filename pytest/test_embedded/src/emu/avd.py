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
import configparser
import gzip
import logging
import os
import platform
import re
import shutil
import subprocess
import enum
from itertools import chain
from pathlib import Path
from typing import Iterator, Optional

from emu.template_writer import TemplateWriter
from emu.utils import system_cpu


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

class SdkManagerChannel(enum.Enum):
    # Values are defined by sdkmanager binary
    STABLE = 0
    BETA = 1
    DEV = 2
    CANARY = 3

class FetcherSystemImages:
    def __init__(self, fetcher: Path):
        """A Class that can be used to install system images.

        Args:
            fetcher: Path - Path to the fetcher utilitya.
        """
        self._fetcher = fetcher

    def find_and_unpack(self, api: str, abi: str, tag: str) -> Optional[dict[str, str]]:
        """Installs the system image using the fetcher binary.

           The fetcher binary handles caching and clearing out older images.

        Args:
            api (str): Api level, usually a number, or first letter of desert
            abi (str): The abi of interest, one of x86|x86_64|arm64-v8a
            tag (str): Tag of interest, one of default|google_apis|google_apis_playstore|
                       google_apis_tablet|android-desktop|android-wear|android-tv|google-xr

        Returns:
            dict[str, str]:  A dictionary with api, tag, abi, and cpu.

        Raises:
            SystemImageDownloadFailed: If we failed to obtain the given image
        """
        return self.install(api, abi, tag)

    def find_and_unpack_ab(
        self, api: str, abi: str, tag: str, build_id: str, target: str, resource: str
    ) -> Optional[dict[str, str]]:
        """Installs the system image using the fetcher binary from android build.

           The fetcher binary handles caching and clearing out older images.

        Args:
            api (str): Api level, usually a number, or first letter of desert
            abi (str): The abi of interest, one of x86|x86_64|arm64-v8a
            tag (str): Tag of interest, one of default|google_apis|google_apis_playstore|
                       google_apis_tablet|android-desktop|android-wear|android-tv|google-xr
            build_id (str): Android Build ID.
            target (str): Build target.
            resource (str): Resource file to download.

        Returns:
            dict[str, str]:  A dictionary with api, tag, abi, and cpu.

        Raises:
            SystemImageDownloadFailed: If we failed to obtain the given image
        """
        return self.install(api, abi, tag, f"ab,{build_id},{target},{resource}")

    def install(
        self, api: str, abi: str, tag: str = "google_apis", fetch_target: str = ""
    ) -> dict[str, str]:
        """Installs the system image using the fetcher binary.

           The fetcher binary handles caching and clearing out older images.

        Args:
            api (str): Api level, usually a number, or first letter of desert
            abi (str): The abi of interest, one of x86|x86_64|arm64-v8a
            tag (str): Tag of interest, one of default|google_apis|google_apis_playstore|
                       google_apis_tablet|android-desktop|android-wear|android-tv|google-xr
            fetch_target(str): Optional fetcher target to use instead of deferring to sdkmanager.

        Raises:
            SystemImageDownloadFailed: If we failed to obtain the given image

        Returns:
            dict[str, str]:  A dictionary with api, tag, abi, and cpu.
        """
        channel = SdkManagerChannel.STABLE
        if tag == "google-xr":
            # Use Canary releases for XR
            channel = SdkManagerChannel.CANARY
        if fetch_target:
            logging.info(f"Installing {fetch_target} on channel:{channel.name}")
        else:
            logging.info(f"Installing 'system-images;android-{api};{tag};{abi}' on channel:{channel.name}")
            fetch_target = f"sdk,android-{api},{tag},{abi},{channel.value}"
        download = subprocess.run(
            [
                self._fetcher,
                fetch_target,
            ],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            check=False,
        )
        if download.returncode != 0:
            logging.error("fetcher: %s", download.stderr.decode("UTF-8"))
            raise SystemImageDownloadFailed(
                f"Failed to obtain image system-images;android-{api};{abi};{tag}"
            )
        return {
            "api": api,
            "tag": tag,
            "abi": abi,
            "image_dir": os.path.join(download.stdout.decode("UTF-8").strip(), abi),
        }


class SystemImages:
    IMAGE = re.compile(
        r".*android-([\d.]+)[\/\\](default|google_apis|google_apis_playstore|google_apis_tablet|android-desktop|android-wear|android-tv|google-xr)[\/\\](x86|x86_64|arm64-v8a)[\/\\]system.img(.gz)?$"
    )

    def __init__(self, sdk_root: Path = Path(os.environ.get("ANDROID_SDK_ROOT", "."))):
        """A Class that can be used to discover and install system images

        Args:
            sdk_root (Path, optional): The sdk root to use. Defaults to "$ANDROID_SDK_ROOT" environment.

        Raises:
            SdkManagerDoesNotExist: If the sdk manager executable was not found in the sdk root
        """
        abs_root = Path(sdk_root).absolute()
        self.sys_root = abs_root / "system-images"
        self.sdk_root = abs_root

        if not self.sys_root.exists():
            logging.warning(
                f"The directory {self.sys_root} does not exist, creating it"
            )
            self.sys_root.resolve().absolute().mkdir(parents=True)

        self.sdk_manager = abs_root / "cmdline-tools" / "latest" / "bin" / "sdkmanager"

        if platform.system() == "Windows":
            self.sdk_manager = self.sdk_manager.with_suffix(".bat")

        if not self.sdk_manager.exists():
            raise SdkManagerDoesNotExist(
                f"The sdk manager {self.sdk_manager} was not found in {self.sys_root}. Is ANDROID_SDK_ROOT set properly?"
            )

    def available(self) -> Iterator[dict[str, str]]:
        """An iterator over all available system images

        Yields:
            Iterator[dict[str, str]]: A dictionary with api, tag, abi, and cpu.

        Raises:
            SystemImageDirectoryDoesNotExist: If no system-images directory was find under the root
        """
        if not self.sys_root.exists():
            raise SystemImageDirectoryDoesNotExist(f"The directory {self.sys_root} does not exist (yet?). Is ANDROID_SDK_ROOT set properly?")
        for x in self._recursive_iglob(self.sys_root):
            m = self.IMAGE.match(str(x))
            if m:
                yield {
                    "api": m.group(1),
                    "tag": m.group(2),
                    "abi": m.group(3),
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
            tag (str): Tag of interest, one of default|google_apis|google_apis_playstore|
                       google_apis_tablet|android-desktop|android-wear|android-tv|google-xr

        Returns:
            Optional[dict[str, str]]:  A dictionary with api, tag, abi, and cpu.

        Raises:
            SystemImageDirectoryDoesNotExist: If no system-images directory was find under the root
        """
        return next(
            (
                x
                for x in self.available()
                if x["api"] == api and x["abi"] == abi and x["tag"] == tag
            ),
            None,
        )

    def find_and_unpack_ab(
        self, api: str, abi: str, tag: str, build_id: str, target: str, resource: str
    ) -> Optional[dict[str, str]]:
        """Unsupported."""
        raise NotImplementedError("Android Build is only supported with --fetcher")

    def find_and_unpack(self, api: str, abi: str, tag: str) -> Optional[dict[str, str]]:
        """Finds the system image with the given api, abi and tag, and makes
           sure the image is runnable by the emulator.

           This is done by decompressing the compressed gzip files that might exist
           in the discovered emulator directory (files with a .gz extension).

           Files that already have been decompressed will be skipped. For example if
           system.img exists then system.img.gz will not be decompressed.

        Args:
            api (str): Api level, usually a number, or first letter of desert
            abi (str): The abi of interest, one of x86|x86_64|arm64-v8a
            tag (str): Tag of interest, one of default|google_apis|google_apis_playstore|
                       google_apis_tablet|android-desktop|android-wear|android-tv|google-xr

        Returns:
            Optional[dict[str, str]]:  A dictionary with api, tag, abi, and cpu.

        Raises:
            SystemImageDirectoryDoesNotExist: If no system-images directory was find under the root
        """
        image = self.find(api, abi, tag)
        if image is None:
            return None

        image_dir: Path = self.sdk_root / image["image_dir"]
        blocksize: int = 8192  # 8kb
        for file_gz in image_dir.glob("*.gz"):
            file: Path = file_gz.parent / file_gz.stem
            if file.exists() and os.path.getmtime(file) > os.path.getmtime(file_gz):
                logging.warning(
                    "The %s is newer than %s, no extraction needed.", file, file_gz
                )
            else:
                logging.info("Be patient extracting %s...", file_gz)
                with gzip.open(file_gz, "rb") as file_gz_in:
                    with open(file, "wb") as file_gz_out:
                        shutil.copyfileobj(file_gz_in, file_gz_out, blocksize)
        return image

    def install(self, api: str, abi: str, tag: str = "google_apis") -> dict[str, str]:
        """Installs the system image with the given api, abi and tag.

        Args:
            api (str): Api level, usually a number, or first letter of desert
            abi (str): The abi of interest, one of x86|x86_64|arm64-v8a
            tag (str): Tag of interest, one of default|google_apis|google_apis_playstore|
                       google_apis_tablet|android-desktop|android-wear|android-tv|google-xr

        Raises:
            SystemImageDownloadFailed: If we failed to obtain the given image

        Returns:
            dict[str, str]:  A dictionary with api, tag, abi, and cpu.
        """
        # # 0 (Stable), 1 (Beta), 2 (Dev), and 3 (Canary).
        channel = SdkManagerChannel.STABLE
        if tag == "google-xr":
            # Use Canary releases for XR
            channel = SdkManagerChannel.CANARY
        logging.info(f"Installing 'system-images;android-{api};{tag};{abi}' on channel:{channel.name}")
        download = subprocess.run(
            [
                self.sdk_manager,
                f"system-images;android-{api};{tag};{abi}",
                f"--channel={channel.value}",
            ],
            stderr=subprocess.PIPE,
            check=False,
        )
        if download.returncode != 0:
            logging.error("sdkmanager: %s", download.stderr.decode("UTF-8"))
            raise SystemImageDownloadFailed(
                f"Failed to obtain image system-images;android-{api};{abi};{tag}"
            )
        ret = self.find(api, abi, tag)
        if not ret:
            # This may happen if SystemImages.IMAGE regex requires an update
            raise SystemImageDownloadFailed(
                f"Failed to find system-image for {api}-{tag}-{abi}, make sure find regex is up to date."
            )
        return ret

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


class AvdConfig:
    """A simple class that represents a created AVD configuration."""

    def __init__(self, avd_id_ini: Path):
        """Access to an avd configuration.

        The avd_id_ini file should point to the .ini file in the root
        for example:

            ~/.android/avd/33.ini

        Args:
            avd_id_ini (Path): The path to the root ini file.
        """
        self.name = avd_id_ini.with_suffix("").name
        self.avd = self._parse_ini(avd_id_ini)
        self.avd_ini = avd_id_ini
        if "path" in self.avd:
            self.directory = Path(self.avd["path"])
        else:
            self.directory = avd_id_ini.parent / self.avd["path.rel"]
        self.hardware = self._parse_ini(self.directory / "config.ini")

    def _parse_ini(self, simple_ini_file: Path) -> configparser.SectionProxy:
        config_parser = configparser.ConfigParser()
        with open(simple_ini_file, "r", encoding="utf-8") as ini_file:
            lines = chain(("[emu]\n",), ini_file)  # This line does the trick.
            config_parser.read_file(lines)

        return config_parser["emu"]

    def delete(self) -> None:
        """Deletes the created avd."""
        try:
            self.avd_ini.unlink()
        except FileNotFoundError:
            logging.warning("avd_ini %s already removed", self.avd_ini)

        logging.debug("Removing %s", self.directory)
        try:
            if platform.system() == "Windows":
                mycmd = "rmdir {} /s /q".format(self.directory.absolute())
                try:
                    subprocess.check_output(mycmd, shell=True)
                except subprocess.CalledProcessError:
                    logging.warning("Failed to delete %s", self.directory)
            else:
                shutil.rmtree(self.directory.absolute())
        except OSError:
            logging.warning("Failed to remove %s", self.directory)


class AvdWriter:
    """An AvdWriter is able write an avd configuration.

    Attributes:

        avd_home (Path): The avd home directory where the config will be written to.
        imgs (SystemImages): The system images that can be used.
        writer (TemplateWriter): Template writer used to write out configurations
    """

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
        fetcher: Optional[Path] = None,
    ):
        """An AvdWriter can be used to dynamically create avds of a given abi, tag and api level

        The AvdWriter uses a Pixel-2 device as a template and will obtain the required system images
        if they are not available.

        The AVDs will be created in the avd_home directory, and system-images will be placed in the
        sdk_root.

        Args:
            sdk_root (Path, optional): The sdk root to use. Defaults to "$ANDROID_SDK_ROOT" environment.
            avd_home (Path, optional): The sdk root to use. Defaults to "$ANDROID_AVD_HOME" environment, or ~/.android/avd.
            fetcher (Path, optional): Path to the fetcher binary.

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
        if fetcher:
            self.sys_imgs = FetcherSystemImages(fetcher)
        else:
            self.sys_imgs = SystemImages(sdk_root)
        self.writer = TemplateWriter(self.avd_home)

    def _write_config_ini(
        self,
        name: str,
        device_name: str,
        avd: dict[str, str],
        custom_cfg: dict[str, str],
    ) -> None:
        """Writes the custom config ini to the avd_home directory"""
        cfg = self.writer.template_to_dict(f"{device_name}.avd/config.ini", avd)
        cfg.update(custom_cfg)

        cfg_file = f"{name}.avd/config.ini"
        dest = self.avd_home / cfg_file
        logging.info("Writing config.ini to %s (%s)", dest, cfg)
        if not dest.parent.exists():
            os.makedirs(dest.parent)

        with open(dest, "w", encoding="utf-8") as avd_cfg_file:
            for key, value in cfg.items():
                avd_cfg_file.write(f"{key} = {value}\n")

    def _create_avd(
        self,
        api: str,
        abi: str,
        tag: str,
        name: str,
        device_name: str,
        custom_cfg: dict[str, str],
    ) -> AvdConfig:
        if "image.sysdir.1" in custom_cfg:
            logging.warning(
                "Using custom system image: %s", custom_cfg["image.sysdir.1"]
            )
            avd = {
                "api": api,
                "tag": tag,
                "abi": abi,
            }
        elif "android_build" in custom_cfg:
            ab_cfg = custom_cfg["android_build"]
            avd = self.sys_imgs.find_and_unpack_ab(
                api, abi, tag, ab_cfg["build_id"], ab_cfg["target"], ab_cfg["resource"]
            )
        else:
            avd = self.sys_imgs.find_and_unpack(api, abi, tag)
            if not avd:
                logging.warning(
                    "Installing api: %s, abi: %s, tag: %s, this is a very expensive operation, and can easily take up 10 minutes!",
                    api,
                    abi,
                    tag,
                )
                avd = self.sys_imgs.install(api, abi, tag)

        avd["name"] = name
        avd["avd_home"] = self.avd_home
        avd["host_cpu"] = system_cpu()

        self.writer.write_template(f"{device_name}.ini", avd, f"{name}.ini")
        self._write_config_ini(name, device_name, avd, custom_cfg)
        return AvdConfig(self.avd_home / f"{name}.ini")

    def create_from_config(self, config: dict[str, str]) -> AvdConfig:
        """Create a basic avd using the given configuration

        The configuration should have the following entries:

            api (str): Api level, usually a number, or first letter of desert
            abi (str): The abi of the machine. Note that qemu must support this abi!
            tag (str): Tag of interest, one of default|google_apis|google_apis_playstore|
                       google_apis_tablet|android-desktop|android-wear|android-tv|google-xr
            [optional] device.name (str): One of: Pixel2|PixelFold|Nexus7_2013|TV_1080p|WearOS_Square|XR1
                                          Defaults to Pixel2.
            [optional] AvdId (str): The name of the AVD to be created. Defaults to "{api}_{tag}_{abi}_{device_name}"

        Note, you will need to look at the actual templates (templates/Pixel2.avd/config.ini) to see
        which values you can actually pass in as config.

        Note: This can result in downloading the missing system image using sdkmanager. This can be a
        costly operation (>4gb download for some images) and can be time consuming depending on your
        network connection.

        Args:
            config (dict[str, str]): _description_

        Returns:
            AvdConfig: The avd configuration
        """
        abi = config["abi"]
        tag = config["tag.id"]
        abi = "x86" if (tag.endswith("-tv") and abi == "x86_64") else abi
        api = config["api"]
        device_name = config.get("device.name", "Pixel2")

        if not abi in self.SUPPORTED_ABI:
            raise UnsupportedAbiOrCpu(
                f"Abi {abi} is not supported, please use one of: {', '.join(self.SUPPORTED_ABI)}"
            )

        name = config.get("AvdId", f"{api}_{tag}_{abi}_{device_name}")
        avd_cfg = {
            "AvdId": name,
            "tag.id": tag,
            "abi.type": abi,
        }
        avd_cfg.update(config)

        return self._create_avd(api, abi, tag, name, device_name, avd_cfg)

    def create(self, api: str, abi: str, tag: str = "google_apis") -> str:
        """Create a basic avd using the given api, abi and tag.

        The avd is based on a Pixel-2.

        Args:
            api (str): Api level, usually a number, or first letter of desert
            abi (str): The abi of interest, one of x86|x86_64|arm64-v8a
            tag (str): Tag of interest, one of default|google_apis|google_apis_playstore|
                       google_apis_tablet|android-desktop|android-wear|android-tv|google-xr

        Returns:
            AvdConfig: The avd configuration that can be used to launch the emulator
        """
        return self.create_from_config({"abi": abi, "api": api, "tag.id": tag})
