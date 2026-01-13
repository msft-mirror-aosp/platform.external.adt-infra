"""Configuration to run ets."""

import argparse

from sequence import config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    config.add_args(parser)
    parser.add_argument("--abi", help="ABI to run the tests as")
    parser.add_argument(
        "--goldfish_zip", type=config.path_type, help="Path to the goldfish zip"
    )
    parser.add_argument(
        "--android_ets_zip", type=config.path_type, help="Path to the android-ets zip"
    )
    parser.add_argument(
        "--image_extract_dir", type=config.dir_type, help="Path to the extracted image"
    )
    parser.add_argument(
        "--build_tools_extract_dir",
        type=config.dir_type,
        help="Path to the extracted build tools",
    )
    parser.add_argument(
        "--emulator_access_json",
        type=config.path_type,
        help="Path to the emulator_access.json",
    )
    parser.add_argument(
        "--platform_tools_extract_dir",
        type=config.dir_type,
        help="Path to the extracted platform tools",
    )
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> str:
    """Build the config.txtpb.

    NOTE: In the near future this will be built from actual protobuf objects.
    This is currently used to allow the outer layers to functon as expected when
    the protobuf object support is added.
    """
    return _CONFIG_TEMPL % {
        "abi": args.abi,
        "goldfish_zip": args.goldfish_zip,
        "android_ets_zip": args.android_ets_zip,
        "emulator_access_json": args.emulator_access_json,
        "image_extract_dir": args.image_extract_dir,
        "build_tools_extract_dir": args.build_tools_extract_dir,
        "platform_tools_extract_dir": args.platform_tools_extract_dir,
    }


_CONFIG_TEMPL = """
agent:  {
  id:  "goldfish_fetch"
  extract:  {
    path: "%(goldfish_zip)s"
  }
}
agent:  {
  id:  "tradefed_fetch"
  extract:  {
    path:  "%(android_ets_zip)s"
  }
}
agent:  {
  android_home:  {
    extract_dir:  "%(platform_tools_extract_dir)s"
  }
}
agent:  {
  avd:  {
    avd_config_ini:  "avd.ini.displayname=°UTF8"
    avd_config_ini:  "avd.ini.encoding=UTF-8"
    avd_config_ini:  "disk.dataPartition.size=4G"
    avd_config_ini:  "hw.accelerometer=yes"
    avd_config_ini:  "hw.audioInput=yes"
    avd_config_ini:  "hw.battery=yes"
    avd_config_ini:  "hw.camera.back=emulated"
    avd_config_ini:  "hw.camera.front=emulated"
    avd_config_ini:  "hw.cpu.ncore=4"
    avd_config_ini:  "hw.device.hash2=MD5:2fa0e16c8cceb7d385183284107c0c88"
    avd_config_ini:  "hw.device.manufacturer=Google"
    avd_config_ini:  "hw.device.name=Pixel 7 Pro"
    avd_config_ini:  "hw.dPad=no"
    avd_config_ini:  "hw.gps=yes"
    avd_config_ini:  "hw.gpu.enabled=yes"
    avd_config_ini:  "hw.keyboard=yes"
    avd_config_ini:  "hw.lcd.density=560"
    avd_config_ini:  "hw.lcd.height=3120"
    avd_config_ini:  "hw.lcd.width=1440"
    avd_config_ini:  "hw.mainKeys=no"
    avd_config_ini:  "hw.ramSize=4096"
    avd_config_ini:  "hw.sdCard=no"
    avd_config_ini:  "hw.sensors.orientation=yes"
    avd_config_ini:  "hw.sensors.proximity=yes"
    avd_config_ini:  "hw.trackBall=no"
    avd_config_ini:  "skin.dynamic=no"
    avd_config_ini:  "skin.name=1440x3120"
    avd_config_ini:  "skin.path=1440x3120"
    avd_config_ini:  "tag.display=Google Play"
    avd_config_ini:  "tag.id=google_apis_playstore"
    cleanup: true
    extract_dir:  "%(image_extract_dir)s"
  }
}
agent: {
  imports: {
    id: "tradefed"
    src: "results_dir"
  }
  junit_xml_result: {}
}
agent:  {
  imports:  {
    id:  "android_home"
    src:  "android_home"
  }
  imports:  {
    id:  "avd"
    src:  "avd_path"
  }
  imports:  {
    id:  "goldfish_fetch"
    src:  "extract_dir"
  }
  goldfish:  {
    args:  "-wipe-data"
    args:  "-verbose"
    args: "-show-kernel"
    args: "-guest-angle"
    args: "-not-in-bazel"
    args: "-grpc-allowlist"
    args: "%(emulator_access_json)s"
    cleanup: true
    emulator_path:  "emulator"
    max_attempts:  5
  }
}
agent: {
  id: "tradefed"
  imports: {
    id: "tradefed_fetch"
    src: "extract_dir"
  }
  imports: {
    id: "goldfish"
    src: "serial_number"
  }
  imports: {
    id: "goldfish"
    src: "grpc_port"
    dst: "args"
    re_replace: "com.android.tradefed.testtype.AndroidJUnitTest:instrumentation-arg:grpc-port:=${1}"
  }
  tradefed: {
    args: "run"
    args: "commandAndExit"
    args: "ets"
    args: "--abi"
    args: "%(abi)s"
    args: "--test-arg"
    build_tools_extract_dir: "%(build_tools_extract_dir)s"
    platform_tools_extract_dir: "%(platform_tools_extract_dir)s"
    preclean: true
  }
}
"""

if __name__ == "__main__":
    args = parse_args()
    config.main(args, build_config(args))
