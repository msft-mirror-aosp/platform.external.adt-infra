"""Configuration to run cts."""

import argparse

from sequence import agent_common
from sequence import config
from test_seq.proto import test_sequencer_pb2


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--deqp_submodule",
        help="Submodule of deqp to run",
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
    return parser


def get_config(ns: argparse.Namespace) -> list[test_sequencer_pb2.AgentConfig]:
    args = []
    if ns.deqp_submodule:
        args = [
            "cts",
            "-m",
            "CtsDeqpTestCases",
            "--module-arg",
            "CtsDeqpTestCases:include-filter:" + ns.deqp_submodule,
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
        args = ["cts", "-m", ns.module]
    return [
        agent_common.goldfish_fetch(ns),
        agent_common.android_home(ns),
        agent_common.avd(ns),
        agent_common.junit_xml_result(ns),
        agent_common.goldfish(ns),
        agent_common.cts(ns, args),
    ]


if __name__ == "__main__":
    config.main(get_parser(), get_config)
