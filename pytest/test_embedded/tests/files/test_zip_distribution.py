import os
import platform
from pathlib import Path

import pytest

from emu.emulator import BaseEmulator


@pytest.mark.e2e
@pytest.mark.boot
def test_zip_file_contains_all_expected_files(emulator: BaseEmulator):
    emu_root = Path(emulator.exe).parent
    assert emu_root.exists(), "Emulator folder does not exist."

    act_files = [f.name for f in emu_root.iterdir() if f.is_file()]
    assert len(act_files) > 0, f"{emu_root} folder should not be empty."
    for file in get_expected_files():
        assert file in act_files, f"{file} is missing in the Emulator directory."

    act_sub_dirs = [f.name for f in emu_root.iterdir() if f.is_dir()]
    assert len(act_sub_dirs) > 0, f"{emu_root} folder missing sub directories."
    exp_sub_dirs = get_exp_sub_dirs()
    for folder in exp_sub_dirs:
        assert folder in act_sub_dirs, f"{folder} is missing in the Emulator directory."
        sub_dir_files = [f.name for f in Path(os.path.join(emu_root, folder)).iterdir()]
        for file in exp_sub_dirs[folder]:
            assert (
                file in sub_dir_files
            ), f"{file} is missing in the Emulator sub directory {folder}."


def get_expected_files():
    """given a OS environment return the expected files under emulator folder."""
    exp_files = [
        "NOTICE.csv",
        "qsn",
        "qemu-img",
        "crashreport",
        "LICENSE",
        "crashpad_handler",
        "source.properties",
        "emulator-check",
        "NOTICE.txt",
        "netsimd",
        "android-info.txt",
        "mksdcard",
        "nimble_bridge",
        "emulator",
    ]

    exp_files_win = [
        "NOTICE.csv",
        "qsn.exe",
        "qemu-img.exe",
        "crashreport.exe",
        "LICENSE",
        "crashpad_handler.exe",
        "source.properties",
        "emulator-check.exe",
        "NOTICE.txt",
        "netsimd.exe",
        "android-info.txt",
        "mksdcard.exe",
        "nimble_bridge.exe",
        "emulator.exe",
        "android-emu-agents.lib",
        "concrt140.dll",
        "libandroid-emu-agents.dll",
        "libprotobuf.dll",
        "msvcp140.dll",
        "msvcp140_1.dll",
        "msvcp140_2.dll",
        "msvcp140_atomic_wait.dll",
        "msvcp140_codecvt_ids.dll",
        "protobuf.lib",
        "vccorlib140.dll",
        "vcruntime140.dll",
        "vcruntime140_1.dll",
    ]

    if platform.system() == "Windows":
        return exp_files_win
    elif platform.system() == "Linux" or platform.system() == "Darwin":
        return exp_files


def get_exp_sub_dirs():
    """given a OS environment return the expected sub directories and
    files under them.

    """
    exp_sub_dirs = {
        "bin64": ["e2fsck", "fsck.ext4", "mkfs.ext4", "resize2fs", "tune2fs"],
        "include": ["flatbuffers"],
        "lib": [
            "adb_service.proto",
            "emu-original-feature-flags.protobuf",
            "emulator_controller.proto",
            "pc-bios",
            "advancedFeatures.ini",
            "emulated_bluetooth.proto",
            "emulator_stats.proto",
            "pkgconfig",
            "emulated_bluetooth_device.proto",
            "grpc_endpoint_description.proto",
            "snapshot.proto",
            "ca-bundle.pem",
            "hardware-properties.ini",
            "snapshot_service.proto",
            "cmake",
            "hostapd.conf",
            "ui_controller_service.proto",
            "control_socket.proto",
            "emulator_access.json",
            "libflatbuffers.a",
            "waterfall.proto",
        ],
        "lib64": [
            "gles_angle",
            "libandroid-emu-protos.dylib",
            "libprotobuf.dylib",
            "libandroid-emu-agents.dylib",
            "libimage_converter.dylib",
            "libshadertranslator.dylib",
            "libandroid-emu-curl.dylib",
            "libandroid-emu-tracing.dylib",
            "libprotobuf.3.21.12.0.dylib",
            "qt",
            "libandroid-emu-metrics.dylib",
            "libemugl_common.dylib",
            "libprotobuf.32.dylib",
            "vulkan",
        ],
        "resources": [
            "Toren1BD.mtl",
            "Toren1BD.posters",
            "Toren1BD_Main.png",
            "macros",
            "Toren1BD.obj",
            "Toren1BD_Decor.png",
            "macroPreviews",
            "poster.png",
        ],
    }

    exp_sub_dirs_win = {
        "bin64": [
            "e2fsck.exe",
            "resize2fs.exe",
            "tune2fs.exe",
            "cygblkid-1.dll",
            "cygcom_err-2.dll",
            "cyge2p-2.dll",
            "cygext2fs-2.dll",
            "cyggcc_s-1.dll",
            "cygiconv-2.dll",
            "cygintl-8.dll",
            "cyguuid-1.dll",
            "cygwin1.dll",
        ],
        "include": ["flatbuffers"],
        "lib": [
            "adb_service.proto",
            "emu-original-feature-flags.protobuf",
            "emulator_controller.proto",
            "pc-bios",
            "advancedFeatures.ini",
            "emulated_bluetooth.proto",
            "emulator_stats.proto",
            "pkgconfig",
            "emulated_bluetooth_device.proto",
            "grpc_endpoint_description.proto",
            "snapshot.proto",
            "ca-bundle.pem",
            "hardware-properties.ini",
            "snapshot_service.proto",
            "cmake",
            "hostapd.conf",
            "ui_controller_service.proto",
            "emulator_access.json",
            "flatbuffers.lib",
        ],
        "lib64": [
            "gles_angle",
            "libandroid-emu-protos.dll",
            "libprotobuf.dll",
            "libandroid-emu-agents.dll",
            "libimage_converter.dll",
            "libshadertranslator.dll",
            "libandroid-emu-curl.dll",
            "libandroid-emu-tracing.dll",
            "qt",
            "libandroid-emu-metrics.dll",
            "libemugl_common.dll",
            "vulkan",
            "vcruntime140_1.dll",
            "vcruntime140.dll",
            "vccorlib140.dll",
            "msvcp140_codecvt_ids.dll",
            "msvcp140_atomic_wait.dll",
            "msvcp140_2.dll",
            "msvcp140_1.dll",
            "msvcp140.dll",
            "libglib2_windows_msvc-x86_64.dll",
            "gles_swiftshader",
            "gles_mesa",
            "concrt140.dll",
        ],
        "resources": [
            "Toren1BD.mtl",
            "Toren1BD.posters",
            "Toren1BD_Main.png",
            "macros",
            "Toren1BD.obj",
            "Toren1BD_Decor.png",
            "macroPreviews",
            "poster.png",
        ],
        "drivers": [
            "UsbAssist_Install.bat",
            "UsbAssist.sys",
            "UsbAssist.inf",
            "usbassist.cat",
            "Install_Drivers.bat",
            "Android_USB_Assistant_Install.bat",
            "Android_USB_Assistant.inf",
            "Android_USB_Assistant.cat",
        ],
    }

    lib64_linux = [
        "gles_angle",
        "gles_mesa",
        "gles_swiftshader",
        "libandroid-emu-protos.so",
        "libprotobuf.so",
        "libandroid-emu-agents.so",
        "libandroid-emu-shared.so",
        "libimage_converter.so",
        "libshadertranslator.so",
        "libandroid-emu-curl.so",
        "libandroid-emu-tracing.so",
        "libprotobuf.so.3.21.12.0",
        "qt",
        "libandroid-emu-metrics.so",
        "libemugl_common.so",
        "libprotobuf.so.32",
        "vulkan",
        "libandroid-webrtc.so",
        "libc++.so",
        "libc++.so.1",
        "libtcmalloc_minimal.so.4",
    ]

    if platform.system() == "Windows":
        exp_sub_dirs_win["qemu"] = ["windows-x86_64"]
        return exp_sub_dirs_win
    elif platform.system() == "Linux":
        exp_sub_dirs["qemu"] = ["linux-x86_64"]
        exp_sub_dirs["lib"].append("ice_config.proto")
        exp_sub_dirs["lib"].append("rtc_service.proto")
        exp_sub_dirs["lib"].append("rtc_service_v2.proto")
        exp_sub_dirs["lib64"] = lib64_linux
        return exp_sub_dirs
    elif platform.system() == "Darwin":
        if platform.processor() == "arm":
            exp_sub_dirs["qemu"] = ["darwin-aarch64"]
            return exp_sub_dirs
        else:
            exp_sub_dirs["qemu"] = ["darwin-x86_64"]
            return exp_sub_dirs
