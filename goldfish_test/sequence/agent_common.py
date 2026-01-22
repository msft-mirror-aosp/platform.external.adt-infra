"""Common agent configurations."""

import argparse

from test_seq.proto import android_home_pb2
from test_seq.proto import avd_pb2
from test_seq.proto import extract_pb2
from test_seq.proto import goldfish_pb2
from test_seq.proto import junit_xml_result_pb2
from test_seq.proto import test_sequencer_pb2
from test_seq.proto import tradefed_pb2


def android_home(ns: argparse.Namespace) -> test_sequencer_pb2.AgentConfig:
    return test_sequencer_pb2.AgentConfig(
        android_home=android_home_pb2.AndroidHome(
            extract_dir=ns.platform_tools_extract_dir,
        )
    )


def avd(ns: argparse.Namespace) -> test_sequencer_pb2.AgentConfig:
    return test_sequencer_pb2.AgentConfig(
        avd=avd_pb2.AVD(
            avd_config_ini=[
                "avd.ini.displayname=UTF8🤖",
                "avd.ini.encoding=UTF-8",
                "disk.dataPartition.size=4G",
                "hw.accelerometer=yes",
                "hw.audioInput=yes",
                "hw.battery=yes",
                "hw.camera.back=emulated",
                "hw.camera.front=emulated",
                "hw.cpu.ncore=4",
                "hw.device.hash2=MD5:2fa0e16c8cceb7d385183284107c0c88",
                "hw.device.manufacturer=Google",
                "hw.device.name=Pixel 7 Pro",
                "hw.dPad=no",
                "hw.gps=yes",
                "hw.gpu.enabled=yes",
                "hw.keyboard=yes",
                "hw.lcd.density=560",
                "hw.lcd.height=3120",
                "hw.lcd.width=1440",
                "hw.mainKeys=no",
                "hw.ramSize=4096",
                "hw.sdCard=no",
                "hw.sensors.orientation=yes",
                "hw.sensors.proximity=yes",
                "hw.trackBall=no",
                "skin.dynamic=no",
                "skin.name=1440x3120",
                "skin.path=1440x3120",
                "tag.display=Google Play",
                "tag.id=google_apis_playstore",
            ],
            cleanup=True,
            extract_dir=ns.image_extract_dir,
        )
    )


def ets(ns: argparse.Namespace) -> test_sequencer_pb2.AgentConfig:
    return test_sequencer_pb2.AgentConfig(
        tradefed=tradefed_pb2.Tradefed(
            args=[
                "run",
                "commandAndExit",
                "ets",
                "--abi",
                ns.abi,
                "--test-arg",
            ],
            build_tools_extract_dir=ns.build_tools_extract_dir,
            platform_tools_extract_dir=ns.platform_tools_extract_dir,
            preclean=True,
        ),
        imports=[
            test_sequencer_pb2.Import(
                id="tradefed_fetch",
                src="extract_dir",
            ),
            test_sequencer_pb2.Import(
                id="goldfish",
                src="serial_number",
            ),
            test_sequencer_pb2.Import(
                id="goldfish",
                src="grpc_port",
                dst="args",
                re_replace="com.android.tradefed.testtype.AndroidJUnitTest:instrumentation-arg:grpc-port:=${1}",
            ),
        ],
    )


def goldfish(ns: argparse.Namespace) -> test_sequencer_pb2.AgentConfig:
    return test_sequencer_pb2.AgentConfig(
        goldfish=goldfish_pb2.GoldFish(
            args=[
                "-wipe-data",
                "-verbose",
                "-show-kernel",
                "-guest-angle",
                "-not-in-bazel",
                "-grpc-allowlist",
                ns.emulator_access_json,
            ],
            cleanup=True,
            emulator_path="emulator/emulator",
            max_attempts=5,
        ),
        imports=[
            test_sequencer_pb2.Import(
                id="android_home",
                src="android_home",
            ),
            test_sequencer_pb2.Import(
                id="avd",
                src="avd_path",
            ),
            test_sequencer_pb2.Import(
                id="goldfish_fetch",
                src="extract_dir",
            ),
        ],
    )


def goldfish_fetch(ns: argparse.Namespace) -> test_sequencer_pb2.AgentConfig:
    return test_sequencer_pb2.AgentConfig(
        id="goldfish_fetch",
        extract=extract_pb2.Extract(path=ns.goldfish_zip),
    )


def junit_xml_result(ns: argparse.Namespace) -> test_sequencer_pb2.AgentConfig:
    return test_sequencer_pb2.AgentConfig(
        junit_xml_result=junit_xml_result_pb2.JUnitXMLResult(),
        imports=[
            test_sequencer_pb2.Import(
                id="tradefed",
                src="results_dir",
            ),
        ],
    )


def tradefed_fetch(ns: argparse.Namespace) -> test_sequencer_pb2.AgentConfig:
    return test_sequencer_pb2.AgentConfig(
        id="tradefed_fetch",
        extract=extract_pb2.Extract(path=ns.tradefed_zip),
    )
