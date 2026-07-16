"""Configuration to run cts."""

import argparse

from sequence import agent_common
from sequence import config
from test_seq.proto import test_sequencer_pb2

_APE_API_KEY = "secret://projects/android-devtools-emulator/secrets/android-emulator-ape-api-key/versions/latest"


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--submodule",
        help="Submodule to run",
    )
    parser.add_argument(
        "--media_extract_dir",
        type=config.dir_type,
        help="Path to the extracted media files",
    )
    parser.add_argument(
        "--module",
        help="Individual cts module to run",
    )
    parser.add_argument(
        "--plan_path",
        type=config.path_type,
        help="Path to the plan file to run",
    )
    parser.add_argument(
        "--suite",
        help="XTS suite to run",
    )
    return parser


def get_config(ns: argparse.Namespace) -> list[test_sequencer_pb2.AgentConfig]:
    args = []
    if ns.submodule:
        suite_name = ns.suite
        if suite_name == "sts":
            suite_name = "sts-dynamic-full"
        args = [
            suite_name,
            "-m",
            ns.module,
            "--module-arg",
            ns.module + ":include-filter:" + ns.submodule,
        ]
    elif ns.media_extract_dir:
        args = [
            "cts",
            "-m",
            ns.module,
            "--module-arg",
            ns.module + ":has-server-side-config:false",
            "--module-arg",
            ns.module + ":local-media-path:" + ns.media_extract_dir,
        ]
    elif ns.plan_path:
        args = [ns.plan_path]
    else:
        suite_name = ns.suite
        if suite_name == "sts":
            suite_name = "sts-dynamic-full"
        args = [suite_name, "-m", ns.module]
    tradefed = agent_common.cts(ns, args)
    if ns.suite == "gts":
        tradefed.tradefed.ape_api_key = _APE_API_KEY
    return [
        agent_common.goldfish_fetch(ns),
        agent_common.android_home(ns),
        agent_common.avd(ns),
        agent_common.junit_xml_result(ns),
        agent_common.goldfish(ns),
        tradefed,
    ]


if __name__ == "__main__":
    config.main(get_parser(), get_config)
