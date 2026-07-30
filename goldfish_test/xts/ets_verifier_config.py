"""Configuration to run cts verifier via ets."""

import argparse
import os

from sequence import agent_common
from sequence import config
from test_seq.proto import test_sequencer_pb2


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", help="Module to run")
    parser.add_argument("--window", action="store_true", default=False, help="Run emulator with GUI window")
    parser.add_argument("--no-window", "--headless", dest="window", action="store_false", help="Run emulator in headless mode without GUI window")
    return parser


def get_config(ns: argparse.Namespace) -> list[test_sequencer_pb2.AgentConfig]:
    os.environ["CTS_APK_PATH"] = ns.cts_verifier_extract_dir + "/android-cts-verifier/CtsVerifier.apk"
    return [
        agent_common.goldfish_fetch(ns),
        agent_common.tradefed_fetch(ns),
        agent_common.android_home(ns),
        agent_common.avd(ns),
        agent_common.junit_xml_result(ns),
        agent_common.goldfish_grpc(ns),
        # Enable the hidden api.
        agent_common.adb(
            ns, ["shell", "settings", "put", "global", "hidden_api_policy", "1"]
        ),
        # Install CTS Verifier.
        agent_common.adb(
            ns, ["install", "-r", "-g", "android-cts-verifier/CtsVerifier.apk"],
            run_dir=ns.cts_verifier_extract_dir,
        ),
        # Allow CTS Verifier to read device identifiers.
        agent_common.adb(
            ns,
            [
                "shell",
                "appops",
                "set",
                "com.android.cts.verifier",
                "android:read_device_identifiers",
                "allow",
            ],
        ),
        # Disable MANAGE_EXTERNAL_STORAGE permission for CTS Verifier.
        agent_common.adb(
            ns,
            [
                "shell",
                "appops",
                "set",
                "com.android.cts.verifier",
                "MANAGE_EXTERNAL_STORAGE",
                "0",
            ],
        ),
        # Enable test api access for CTS Verifier.
        agent_common.adb(
            ns,
            [
                "shell",
                "am",
                "compat",
                "enable",
                "ALLOW_TEST_API_ACCESS",
                "com.android.cts.verifier",
            ],
        ),
        # Disable TURN_SCREEN_ON permission for CTS Verifier.
        agent_common.adb(
            ns,
            [
                "shell",
                "appops",
                "set",
                "com.android.cts.verifier",
                "TURN_SCREEN_ON",
                "0",
            ],
        ),
        agent_common.ets_verifier(ns, ns.module),
        # Pull CTS Verifier results.
        agent_common.adb(
            ns, ["pull", "/sdcard/verifierReports", "verifierReports"],
            run_dir=os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR"),
        ),
    ]


if __name__ == "__main__":
    config.main(get_parser(), get_config)

