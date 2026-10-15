"""Configuration to run ets."""

import argparse
import platform

from sequence import agent_common
from sequence import config
from test_seq.proto import test_sequencer_pb2


def _wait_for_network_connectivity(
    ns: argparse.Namespace, goldfish_id: str = "goldfish"
) -> test_sequencer_pb2.AgentConfig:
    """Ensures guest WiFi is connected and host gateway 10.0.2.2 is reachable (b/571293062)."""
    return agent_common.adb(
        ns,
        [
            "shell",
            "svc wifi enable; "
            "svc data enable; "
            "for i in $(seq 1 10); do "
            "if ping -c 1 -W 1 10.0.2.2 >/dev/null 2>&1; then exit 0; fi; "
            "cmd wifi connect-network AndroidWifi open >/dev/null 2>&1; "
            "sleep 2; "
            "done; "
            "ping -c 1 -W 2 10.0.2.2",
        ],
        timeout_seconds=30,
        goldfish_id=goldfish_id,
    )


def get_config(ns: argparse.Namespace) -> list[test_sequencer_pb2.AgentConfig]:
    # TODO: b/553593925 Skip snapshots on macOS until the bug is fixed.
    # b/553593925, revert if happens again
    # btw, to trigger a test, bump b to 6: b = 5
    no_snapshot = False
    skip_relaunch = bool(ns.skip_snapshot_relaunch)
    # Cold boot pass, then this many {shut down (saves the snapshot), relaunch from the snapshot,
    # pass} rounds, instead of the single ETS_SNAPSHOT pass.
    relaunch_rounds = int(ns.snapshot_relaunch_rounds or 0)

    ret = [
        agent_common.goldfish_fetch(ns),
        agent_common.tradefed_fetch(ns),
        agent_common.android_home(ns),
        agent_common.avd_ets(ns),
        agent_common.crash_report(),
    ]
    if relaunch_rounds:
        ret.extend(
            [
                agent_common.junit_xml_result_ets_close(ns),
                agent_common.junit_xml_result(ns),
            ]
        )
        for r in range(1, relaunch_rounds + 1):
            ret.append(
                agent_common.junit_xml_result_for(ns, agent_common.ets_load_id(r))
            )
            if r < relaunch_rounds:
                ret.append(
                    agent_common.junit_xml_result_for(
                        ns, agent_common.ets_close_load_id(r)
                    )
                )
        ret.append(agent_common.goldfish_grpc(ns))
    elif no_snapshot:
        ret.extend(
            [
                agent_common.junit_xml_result_ets_close(ns),
                agent_common.junit_xml_result(ns),
            ]
        )
        gf = agent_common.goldfish_grpc(ns)
        gf.goldfish.args.append("-no-snapshot")
        ret.append(gf)
    elif skip_relaunch:
        ret.extend(
            [
                agent_common.junit_xml_result_ets_close(ns),
                agent_common.junit_xml_result(ns),
                agent_common.goldfish_grpc(ns),
            ]
        )
    else:
        ret.extend(
            [
                agent_common.junit_xml_result_ets_snapshot(ns),
                agent_common.junit_xml_result_ets_close(ns),
                agent_common.junit_xml_result(ns),
                agent_common.goldfish_grpc(ns),
            ]
        )

    ret.extend(
        [
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
                ns,
                ["shell", "pm", "disable-user", "--user", "0", "com.android.vending"],
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
                ns,
                [
                    "shell",
                    "pm",
                    "disable-user",
                    "--user",
                    "0",
                    "com.google.android.gms",
                ],
            ),
            # Disable Google Services Framework (GSF) to prevent related background wakeups
            agent_common.adb(
                ns,
                [
                    "shell",
                    "pm",
                    "disable-user",
                    "--user",
                    "0",
                    "com.google.android.gsf",
                ],
            ),
            # Force-stop the specific services known to jam the broadcast queue, these
            # seem to go down frequently
            agent_common.adb(ns, ["shell", "am", "force-stop", "com.android.settings"]),
            agent_common.adb(
                ns, ["shell", "am", "force-stop", "com.google.android.bluetooth"]
            ),
            agent_common.adb(ns, ["shell", "am", "force-stop", "com.android.phone"]),
            agent_common.adb(
                ns, ["shell", "am", "force-stop", "com.google.android.gms"]
            ),
            # Hide all "App has stopped" and "App isn't responding" dialogs
            agent_common.adb(
                ns, ["shell", "settings", "put", "global", "hide_error_dialogs", "1"]
            ),
            # Disable window, transition, and animator scaling
            agent_common.adb(
                ns,
                ["shell", "settings", "put", "global", "window_animation_scale", "0.0"],
            ),
            agent_common.adb(
                ns,
                [
                    "shell",
                    "settings",
                    "put",
                    "global",
                    "transition_animation_scale",
                    "0.0",
                ],
            ),
            agent_common.adb(
                ns,
                [
                    "shell",
                    "settings",
                    "put",
                    "global",
                    "animator_duration_scale",
                    "0.0",
                ],
            ),
            agent_common.adb(ns, ["shell", "am", "kill-all"]),
            # Ensure all teardown broadcasts have flushed before yielding to the test runner
            agent_common.adb(ns, ["shell", "am", "wait-for-broadcast-barrier"]),
            agent_common.adb(
                ns, ["shell", "am", "wait-for-broadcast-idle"], timeout_seconds=180
            ),
            _wait_for_network_connectivity(ns, goldfish_id="goldfish"),
            (
                agent_common.ets_cold_boot_phase(ns)
                if relaunch_rounds
                else agent_common.ets(ns)
            ),
            agent_common.ets_close(ns),
        ]
    )
    if relaunch_rounds:
        for r in range(1, relaunch_rounds + 1):
            ret.extend(
                [
                    agent_common.goldfish_load_phase(ns, r),
                    _wait_for_network_connectivity(
                        ns, goldfish_id=agent_common.goldfish_load_id(r)
                    ),
                    agent_common.ets_load_phase(ns, r),
                ]
            )
            if r < relaunch_rounds:
                ret.append(
                    agent_common.ets_close(
                        ns,
                        id=agent_common.ets_close_load_id(r),
                        goldfish_id=agent_common.goldfish_load_id(r),
                    )
                )
    elif not no_snapshot and not skip_relaunch:
        ret.extend(
            [
                agent_common.goldfish_load_snapshot_grpc(ns),
                _wait_for_network_connectivity(ns, goldfish_id="goldfish_snapshot"),
                agent_common.ets_snapshot(ns),
            ]
        )
    return ret


if __name__ == "__main__":
    config.main(argparse.ArgumentParser(description=__doc__), get_config)
