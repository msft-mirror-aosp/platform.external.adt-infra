"""Configuration to run cts verifier via ets."""

import argparse
import os

from sequence import agent_common
from sequence import config
from test_seq.proto import test_sequencer_pb2


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", help="Module to run")
    parser.add_argument(
        "--window",
        action="store_true",
        default=False,
        help="Run emulator with GUI window",
    )
    parser.add_argument(
        "--no-window",
        "--headless",
        dest="window",
        action="store_false",
        help="Run emulator in headless mode without GUI window",
    )
    return parser


def get_config(ns: argparse.Namespace) -> list[test_sequencer_pb2.AgentConfig]:
    os.environ["CTS_APK_PATH"] = (
        ns.cts_verifier_extract_dir + "/android-cts-verifier/CtsVerifier.apk"
    )
    return [
        agent_common.goldfish_fetch(ns),
        agent_common.tradefed_fetch(ns),
        agent_common.android_home(ns),
        agent_common.avd(ns),
        agent_common.junit_xml_result(ns),
        agent_common.goldfish_grpc(ns),
        agent_common.adb(ns, ["wait-for-device"]),
        agent_common.ets_verifier(ns, ns.module),
        # Pull CTS Verifier results.
        agent_common.adb(
            ns,
            ["pull", "/sdcard/verifierReports", "verifierReports"],
            run_dir=os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR"),
        ),
    ]


if __name__ == "__main__":
    config.main(get_parser(), get_config)
