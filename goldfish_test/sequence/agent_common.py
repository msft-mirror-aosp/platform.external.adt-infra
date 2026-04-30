"""Common agent configurations."""

import argparse
import os

from test_seq.proto import adb_pb2
from test_seq.proto import android_home_pb2
from test_seq.proto import avd_pb2
from test_seq.proto import extract_pb2
from test_seq.proto import goldfish_pb2
from test_seq.proto import junit_xml_result_pb2
from test_seq.proto import test_sequencer_pb2
from test_seq.proto import tradefed_pb2


def adb(ns: argparse.Namespace, args: list[str]) -> test_sequencer_pb2.AgentConfig:
    return test_sequencer_pb2.AgentConfig(
        adb=adb_pb2.ADB(
            args=args,
        ),
        imports = [
            test_sequencer_pb2.Import(
                id="android_home",
                src="android_home",
            ),
            test_sequencer_pb2.Import(
                id="goldfish",
                src="serial_number",
            ),
        ]
    )


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


def avd_ets(ns: argparse.Namespace) -> test_sequencer_pb2.AgentConfig:
    ret = avd(ns)
    ret.avd.avd_config_ini[:] = ["avd.ini.displayname=UTF8🤖"]
    return ret


def cts(ns: argparse.Namespace, args: list[str]) -> test_sequencer_pb2.AgentConfig:
    ac = _tradefed(ns)
    ac.tradefed.extract_dir = ns.tradefed_extract_dir
    ac.tradefed.args.extend(args)
    ac.tradefed.args.extend(
        [
            "--skip-preconditions",
            "--skip-all-system-status-check",
            "--no-has-server-side-config",
            "-l",
            "INFO",
        ]
    )
    ac.imports.extend(
        [
            test_sequencer_pb2.Import(
                id="tradefed",
                src="has_retry_data",
                dst="retry",
            ),
        ]
    )
    return ac


def _ets(ns: argparse.Namespace) -> test_sequencer_pb2.AgentConfig:
    ac = _tradefed(ns)
    ac.imports.append(
        test_sequencer_pb2.Import(
            id="tradefed_fetch",
            src="extract_dir",
        ),
    )
    return ac


def ets(ns: argparse.Namespace) -> test_sequencer_pb2.AgentConfig:
    ac = _ets(ns)
    ac.tradefed.args.extend(
        [
            ns.ets_plan,
            "--abi",
            ns.abi,
            "--retry-strategy",
            "RETRY_ANY_FAILURE",
            "--max-testcase-run-count",
            "3",
            "--module-arg",
            "VulkanAppTest:set-option:apk_path:"
            + os.path.join(ns.hellovk_extract_dir, "hellovk", "hellovk.apk"),
            "--test-arg",
        ]
    )
    ac.imports.append(
        test_sequencer_pb2.Import(
            id="goldfish",
            src="grpc_port",
            dst="args",
            re_replace="com.android.tradefed.testtype.AndroidJUnitTest:instrumentation-arg:grpc-port:=${1}",
        ),
    )
    return ac


def ets_close(ns: argparse.Namespace) -> test_sequencer_pb2.AgentConfig:
    ac = _ets(ns)
    ac.id = "ets_close"
    # The test closes the emulator so tradefed cannot connect to it via adb or an error will be
    # raised when it closes.
    imps = [i for i in ac.imports if i.src != "serial_number"]
    del ac.imports[:]
    ac.imports.extend(imps)
    ac.tradefed.args.extend(
        [
            "ets",
            "-m",
            "CloseEmulatorTest",
            "--abi",
            ns.abi,
            "--null-device",
        ]
    )
    ac.imports.extend(
        [
            test_sequencer_pb2.Import(
                id="goldfish",
                src="grpc_port",
                dst="args",
                re_replace="--module-arg=CloseEmulatorTest:set-option:grpc_port:${1}",
            ),
            test_sequencer_pb2.Import(
                id="goldfish",
                src="serial_number",
                dst="args",
                re_replace="--module-arg=CloseEmulatorTest:set-option:emu_serial:${1}",
            ),
        ]
    )
    return ac


def ets_external(ns: argparse.Namespace, serial_number: str, grpc_port: str) -> test_sequencer_pb2.AgentConfig:
    ac = ets(ns)
    imps = [i for i in ac.imports if i.id != "goldfish"]
    del ac.imports[:]
    ac.imports.extend(imps)
    ac.tradefed.serial_number.append(serial_number)
    ac.tradefed.args.append(
        "--test_arg=com.android.tradefed.testtype.AndroidJUnitTest:instrumentation-arg:grpc-port:="
        + grpc_port
    )
    return ac


def goldfish(ns: argparse.Namespace) -> test_sequencer_pb2.AgentConfig:
    return test_sequencer_pb2.AgentConfig(
        goldfish=goldfish_pb2.GoldFish(
            args=[
                "-verbose",
                "-show-kernel",
                "-not-in-bazel",
                "-no-window",
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


def goldfish_grpc(ns: argparse.Namespace) -> test_sequencer_pb2.AgentConfig:
    ac = goldfish(ns)
    ac.goldfish.args.extend(
        [
            "-grpc-allowlist",
            ns.emulator_access_json,
        ]
    )
    return ac


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


def junit_xml_result_ets_close(
    ns: argparse.Namespace,
) -> test_sequencer_pb2.AgentConfig:
    return test_sequencer_pb2.AgentConfig(
        id="junit_xml_ets_close",
        junit_xml_result=junit_xml_result_pb2.JUnitXMLResult(),
        imports=[
            test_sequencer_pb2.Import(
                id="ets_close",
                src="results_dir",
            ),
        ],
    )


def _tradefed(ns: argparse.Namespace) -> test_sequencer_pb2.AgentConfig:
    return test_sequencer_pb2.AgentConfig(
        tradefed=tradefed_pb2.Tradefed(
            args=[
                "run",
                "commandAndExit",
            ],
            build_tools_extract_dir=ns.build_tools_extract_dir,
            platform_tools_extract_dir=ns.platform_tools_extract_dir,
            preclean=True,
        ),
        imports=[
            test_sequencer_pb2.Import(
                id="goldfish",
                src="serial_number",
            ),
        ],
    )


def tradefed_fetch(ns: argparse.Namespace) -> test_sequencer_pb2.AgentConfig:
    return test_sequencer_pb2.AgentConfig(
        id="tradefed_fetch",
        extract=extract_pb2.Extract(path=ns.tradefed_zip),
    )
