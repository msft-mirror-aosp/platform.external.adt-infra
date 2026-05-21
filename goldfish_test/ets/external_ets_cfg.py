"""Configuration to run ets with an external (already running) emulator."""

import argparse
import os
import logging
import pathlib
import platform

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


def get_discovery_directories() -> list[pathlib.Path]:
    """All the discovery directories that can contain emulator discovery files."""
    paths = []

    if "ANDROID_EMULATOR_HOME" in os.environ:
        paths.append(pathlib.Path(os.environ.get("ANDROID_EMULATOR_HOME")))

    if "ANDROID_SDK_HOME" in os.environ:
        paths.append(pathlib.Path(os.environ.get("ANDROID_SDK_HOME")) / ".android")

    if "ANDROID_AVD_HOME" in os.environ:
        paths.append(pathlib.Path(os.environ.get("ANDROID_AVD_HOME")))

    paths.append(pathlib.Path.home() / ".android")

    path = None
    if platform.system() == "Windows":
        if "LOCALAPPDATA" in os.environ:
            path = pathlib.Path(os.environ.get("LOCALAPPDATA")) / "Temp"
            paths.append(path)
            print(f"Windows: Using LOCALAPPDATA Temp dir: {path}")
        if "USERNAME" in os.environ:
            print(
                "Windows Hack: Bazel likely cleared LOCALAPPDATA. Guessing path based on USERNAME."
            )
            path = (
                pathlib.Path("C:/Users")
                / os.environ.get("USERNAME")
                / "AppData"
                / "Local"
                / "Temp"
            )
            print(f"Windows: Guessed Temp dir: {path}")
            paths.append(path)
    elif platform.system() == "Linux":
        if "XDG_RUNTIME_DIR" in os.environ:
            path = pathlib.Path(os.environ.get("XDG_RUNTIME_DIR"))
            print(f"Linux: Using runtime dir: {path}")
            paths.append(path)
        if path is None or not path.exists():
            path = pathlib.Path("/") / "run" / "user" / pathlib.Path(str(os.getuid()))
            print(f"Linux: Using user dir: {path}")
            paths.append(path)
    elif platform.system() == "Darwin" and "USER" in os.environ:
        print(
            "Darwin Hack: Bazel overrides home. Using username to find temporary items."
        )
        path = (
            pathlib.Path("/Users")
            / os.environ.get("USER")
            / "Library"
            / "Caches"
            / "TemporaryItems"
        )
        print(f"Darwin: Using guessed path: {path}")
        paths.append(path)

    result = [p / "avd" / "running" for p in paths if p is not None]
    print(f"Discovery directories to search: {[str(p) for p in result]}")
    return result


def get_running_emulator() -> tuple[str, str]:
    for discovery_dir in get_discovery_directories():
        if not discovery_dir.exists():
            print(f"Skipping non-existent directory: {discovery_dir}")
            continue

        print(f"Scanning directory: {discovery_dir}")
        for p in discovery_dir.glob("pid_*.ini"):
            print(f"Found discovery file: {p}")
            attrs = {}
            for ln in p.read_text().splitlines():
                if "=" in ln:
                    k, v = ln.split("=", 1)
                    attrs[k] = v
            if "port.serial" in attrs and "grpc.port" in attrs:
                print(
                    f"Success! Discovered emulator with serial '{attrs['port.serial']}' and gRPC port '{attrs['grpc.port']}'"
                )
                return "emulator-" + attrs["port.serial"], attrs["grpc.port"]
            else:
                print(
                    f"Warning: Discovery file {p} missing 'port.serial' or 'grpc.port'. Found keys: {list(attrs.keys())}"
                )

    raise FileNotFoundError(
        "No running emulator found. Checked all discovery directories."
    )


if __name__ == "__main__":
    config.main(argparse.ArgumentParser(description=__doc__), get_config)
