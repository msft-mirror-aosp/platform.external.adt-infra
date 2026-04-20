"""Configuration to run ets with an external (already running) emulator.

TODO(kmagic): Support platforms other than linux.
"""

import argparse
import os
import pathlib

from sequence import agent_common
from sequence import config
from test_seq.proto import test_sequencer_pb2


def get_config(ns: argparse.Namespace) -> list[test_sequencer_pb2.AgentConfig]:
    serial_number, grpc_port = get_running_emulator()
    return [
        agent_common.tradefed_fetch(ns),
        agent_common.junit_xml_result(ns),
        agent_common.ets_external(ns, serial_number, grpc_port),
    ]


def get_running_emulator() -> tuple[str, str]:
  base = pathlib.Path("/run", "user", str(os.getuid()), "avd", "running")
  for p in base.glob("pid_*.ini"):
    attrs = {}
    for ln in p.read_text().splitlines():
      if "=" in ln:
        k, v = ln.split("=", 1)
        attrs[k] = v
    return "emulator-" + attrs["port.serial"], attrs["grpc.port"]
  raise FileNotFoundError("No running emulator found.")


if __name__ == "__main__":
    config.main(argparse.ArgumentParser(description=__doc__), get_config)
