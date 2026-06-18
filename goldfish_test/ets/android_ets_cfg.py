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
        agent_common.junit_xml_result_ets_snapshot(ns),
        agent_common.junit_xml_result_ets_close(ns),
        agent_common.junit_xml_result(ns),
        agent_common.goldfish_grpc(ns),
        # Stabilize emulator environment
        # Force Setup Wizard to consider itself complete
        agent_common.adb(
            ns, ["shell", "settings", "put", "global", "device_provisioned", "1"]
        ),
        agent_common.adb(
            ns, ["shell", "settings", "put", "secure", "user_setup_complete", "1"]
        ),
        # Kill the first-boot Phenotype/GMS sync loop by freezing background updaters
        agent_common.adb(
            ns, ["shell", "pm", "disable-user", "--user", "0", "com.android.vending"]
        ),
        agent_common.adb(
            ns,
            [
                "shell",
                "pm",
                "disable-user",
                "--user",
                "0",
                "com.google.android.configupdater",
            ],
        ),
        # Disable Google Play Services (GMS) to stop heavy background syncs and telemetry
        agent_common.adb(
            ns, ["shell", "pm", "disable-user", "--user", "0", "com.google.android.gms"]
        ),
        # Disable Google Services Framework (GSF) to prevent related background wakeups
        agent_common.adb(
            ns, ["shell", "pm", "disable-user", "--user", "0", "com.google.android.gsf"]
        ),
        # Force-stop the specific services known to jam the broadcast queue, these
        # seem to go down frequently
        agent_common.adb(ns, ["shell", "am", "force-stop", "com.android.settings"]),
        agent_common.adb(
            ns, ["shell", "am", "force-stop", "com.google.android.bluetooth"]
        ),
        agent_common.adb(ns, ["shell", "am", "force-stop", "com.android.phone"]),
        agent_common.adb(ns, ["shell", "am", "force-stop", "com.google.android.gms"]),
        # Hide all "App has stopped" and "App isn't responding" dialogs
        agent_common.adb(
            ns, ["shell", "settings", "put", "global", "hide_error_dialogs", "1"]
        ),
        # Disable window, transition, and animator scaling
        agent_common.adb(
            ns, ["shell", "settings", "put", "global", "window_animation_scale", "0.0"]
        ),
        agent_common.adb(
            ns,
            ["shell", "settings", "put", "global", "transition_animation_scale", "0.0"],
        ),
        agent_common.adb(
            ns, ["shell", "settings", "put", "global", "animator_duration_scale", "0.0"]
        ),
        agent_common.adb(ns, ["shell", "am", "kill-all"]),
        # Ensure all teardown broadcasts have flushed before yielding to the test runner
        agent_common.adb(ns, ["shell", "am", "wait-for-broadcast-barrier"]),
        agent_common.adb(
            ns, ["shell", "am", "wait-for-broadcast-idle"], timeout_seconds=180
        ),
        agent_common.ets(ns),
        agent_common.ets_close(ns),
        agent_common.goldfish_load_snapshot_grpc(ns),
        agent_common.ets_snapshot(ns),
    ]


if __name__ == "__main__":
    config.main(argparse.ArgumentParser(description=__doc__), get_config)
