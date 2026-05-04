"""Configuration to run ets."""

import argparse

from sequence import agent_common
from sequence import config
from test_seq.proto import test_sequencer_pb2


def get_config(ns: argparse.Namespace) -> list[test_sequencer_pb2.AgentConfig]:
    return [
        agent_common.goldfish_fetch(ns),
        agent_common.tradefed_fetch(ns),
        agent_common.android_home(ns),
        agent_common.avd_ets(ns),
        agent_common.junit_xml_result_ets_close(ns),
        agent_common.junit_xml_result(ns),
        agent_common.goldfish_grpc(ns),
        # Prevent the play store from updating to avoid a heavy load on the emulator.
        agent_common.adb(ns, ["shell", "pm" ,"disable-user", "com.android.vending"]),
        agent_common.ets(ns),
        agent_common.ets_close(ns),
    ]


if __name__ == "__main__":
    config.main(argparse.ArgumentParser(description=__doc__), get_config)
