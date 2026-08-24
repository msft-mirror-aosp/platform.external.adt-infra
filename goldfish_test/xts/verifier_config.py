import argparse
import subprocess
import os
import shutil
import sys
import threading
import time

from sequence import agent_common
from sequence import config
from test_seq.proto import test_sequencer_pb2
from python.runfiles import Runfiles


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", help="Suite name")
    parser.add_argument(
        "--apk_dir", type=config.dir_type, help="Directory containing CTS verifier APKs"
    )
    parser.add_argument(
        "--build_tools_extract_dir",
        type=config.dir_type,
        help="Directory containing build tools",
    )
    parser.add_argument("--script", help="Script to run")
    parser.add_argument(
        "--dev_mode",
        action="store_true",
        default=False,
        help="Run in automation development mode using TestBuilder",
    )
    parser.add_argument(
        "--collect_tests",
        action="store_true",
        default=False,
        help="Collect all test module labels by scrolling live CtsVerifier UI on device",
    )
    parser.add_argument(
        "--multi_device",
        action="store_true",
        default=False,
        help="Run in multi-device mesh mode (launches DUT and Companion instances)",
    )
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
    # Ensure ~/.android directory exists in Bazel test sandbox for goldfish launcher
    os.makedirs(os.path.expanduser("~/.android"), exist_ok=True)

    if getattr(ns, "multi_device", False):
        agents = [
            agent_common.goldfish_fetch(ns),
            agent_common.android_home(ns),
            agent_common.avd(ns, id="avd_dut", display_name="DUT🤖"),
            agent_common.avd(ns, id="avd_companion", display_name="Companion🤖"),
            agent_common.goldfish(ns, id="goldfish_dut", avd_id="avd_dut", port=5554),
            agent_common.goldfish(
                ns, id="goldfish_companion", avd_id="avd_companion", port=5556
            ),
            agent_common.adb(ns, ["wait-for-device"], goldfish_id="goldfish_dut"),
            agent_common.adb(
                ns,
                [
                    "shell",
                    'while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 1; done',
                ],
                goldfish_id="goldfish_dut",
            ),
            agent_common.adb(ns, ["wait-for-device"], goldfish_id="goldfish_companion"),
            agent_common.adb(
                ns,
                [
                    "shell",
                    'while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 1; done',
                ],
                goldfish_id="goldfish_companion",
            ),
        ]
        completion_target = "goldfish_dut"
    else:
        agents = [
            agent_common.goldfish_fetch(ns),
            agent_common.android_home(ns),
            agent_common.avd(ns),
            agent_common.goldfish(ns),
            agent_common.adb(ns, ["wait-for-device"]),
            agent_common.adb(
                ns,
                [
                    "shell",
                    'while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 1; done',
                ],
            ),  # Wait for boot
        ]
        completion_target = "goldfish"

    if hasattr(ns, "apk_dir") and ns.apk_dir:
        # NOTE: This static adb completion check does not support device reboots because an adb
        # shell command will drop its connection and exit if the emulator reboots.
        # For any CTS Verifier test that requires device rebooting (e.g., policy serialization),
        # you MUST use ets-verifier (Tradefed / ets_verifier_config.py) instead of verifier_config.py,
        # as Tradefed natively supervises adb disconnection and reconnection across reboots.
        agents.append(
            agent_common.adb(
                ns,
                [
                    "shell",
                    "rm -f /sdcard/verifier_done /sdcard/verifier_failed && "
                    "while [ ! -f /sdcard/verifier_done ] && [ ! -f /sdcard/verifier_failed ]; do sleep 0.5; done; "
                    "if [ -f /sdcard/verifier_failed ]; then exit 1; fi",
                ],
                timeout_seconds=2400,
                goldfish_id=completion_target,
            )
        )

    return agents


def test_runner_thread(args, results_dir):
    try:
        runfiles = Runfiles.Create()

        adb_path = (
            runfiles.Rlocation("platform-tools-linux/platform-tools/adb")
            if runfiles
            else None
        )
        if not adb_path or not os.path.exists(adb_path):
            if runfiles:
                adb_path = runfiles.Rlocation(
                    "_main/external/platform-tools-linux/platform-tools/adb"
                )
        if not adb_path or not os.path.exists(adb_path):
            adb_path = shutil.which("adb")

        script_name = getattr(args, "script", "run_all_vibrations_tests.sh")
        if not script_name:
            script_name = "run_all_vibrations_tests.sh"

        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "verifier", script_name
        )

        print(f"Using adb path: {adb_path}")
        while not adb_path or not os.path.exists(adb_path):
            print(f"Waiting for adb binary...")
            time.sleep(1)
            adb_path = shutil.which("adb")

        # Wait for emulator(s) to fully boot
        multi_device = getattr(args, "multi_device", False)
        devices_to_wait = ["emulator-5554", "emulator-5556"] if multi_device else [None]

        for dev_serial in devices_to_wait:
            serial_prefix = ["-s", dev_serial] if dev_serial else []
            print(
                f"Waiting for device {'default' if not dev_serial else dev_serial}..."
            )
            subprocess.run(
                [adb_path] + serial_prefix + ["wait-for-device"], timeout=120
            )

            print(f"Waiting for sys.boot_completed on {dev_serial or 'default'}...")
            while True:
                res = subprocess.run(
                    [adb_path]
                    + serial_prefix
                    + ["shell", "getprop", "sys.boot_completed"],
                    capture_output=True,
                    text=True,
                )
                if res.stdout.strip() == "1":
                    break
                time.sleep(2)

            print(f"Waiting for package manager on {dev_serial or 'default'}...")
            while True:
                res = subprocess.run(
                    [adb_path] + serial_prefix + ["shell", "pm", "path", "android"],
                    capture_output=True,
                    text=True,
                )
                if "package:" in res.stdout:
                    break
                time.sleep(2)

        time.sleep(5)

        # Setup environment for the script
        env = os.environ.copy()

        if multi_device:
            env["DUT_SERIAL"] = "emulator-5554"
            env["COMPANION_SERIAL"] = "emulator-5556"

        # Symlink python3 to sys.executable
        bin_dir = os.path.join(results_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        python3_link = os.path.join(bin_dir, "python3")
        if not os.path.exists(python3_link):
            os.symlink(sys.executable, python3_link)

        env["PATH"] = (
            bin_dir
            + os.pathsep
            + os.path.dirname(adb_path)
            + os.pathsep
            + env.get("PATH", "")
        )
        env["PYTHONPATH"] = (
            os.path.dirname(script_path) + os.pathsep + env.get("PYTHONPATH", "")
        )
        if hasattr(args, "apk_dir") and args.apk_dir:
            env["CTS_APK_PATH"] = os.path.join(
                args.apk_dir, "android-cts-verifier", "CtsVerifier.apk"
            )
        env["CTS_OUTPUT_DIR"] = results_dir

        if getattr(args, "dev_mode", False) or getattr(args, "collect_tests", False):
            builder_script = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "verifier",
                "automation_dev",
                "test_builder.py",
            )
            if getattr(args, "collect_tests", False):
                print(
                    "🛠️  Development Mode Active: Collecting test module labels from live CtsVerifier UI..."
                )
                dev_cmd = [
                    sys.executable,
                    builder_script,
                    "--collect-test-module-names",
                ]
            else:
                raw_subname = (
                    script_name.replace("run_", "")
                    .replace(".sh", "")
                    .replace("_test", "")
                    .replace("_", " ")
                )
                test_subname = " ".join(
                    word.capitalize() for word in raw_subname.split()
                )
                if not test_subname.endswith("Test"):
                    test_subname += " Test"
                print(
                    f"🛠️  Development Mode Active: Launching TestBuilder for '{test_subname}'..."
                )
                dev_cmd = [sys.executable, builder_script, "--test", test_subname]
            p = subprocess.run(dev_cmd, env=env, check=False)
        else:
            log_file = os.path.join(results_dir, "script_run.log")
            print(f"Executing bash script: {script_path}, logging to {log_file}")
            with open(log_file, "w") as f:
                p = subprocess.run(
                    ["bash", script_path], env=env, stdout=f, stderr=subprocess.STDOUT
                )

            print(f"Script finished with exit code {p.returncode}")
            with open(log_file, "r") as f:
                print(f"Script output:\n{f.read()}")

        # Unblock test_seq
        target_serial_prefix = ["-s", "emulator-5554"] if multi_device else []
        if p.returncode != 0:
            print("Script failed! Creating failure marker.")
            subprocess.run(
                [adb_path]
                + target_serial_prefix
                + ["shell", "touch", "/sdcard/verifier_failed"]
            )
        else:
            print("Unblocking test_seq cleanup...")
            subprocess.run(
                [adb_path]
                + target_serial_prefix
                + ["shell", "touch", "/sdcard/verifier_done"]
            )

    except Exception as e:
        print(f"Exception in test_runner_thread: {e}")
        target_serial_prefix = (
            ["-s", "emulator-5554"] if getattr(args, "multi_device", False) else []
        )
        subprocess.run(
            [adb_path]
            + target_serial_prefix
            + ["shell", "touch", "/sdcard/verifier_failed"]
        )


if __name__ == "__main__":
    parser = get_parser()
    args, _ = parser.parse_known_args()

    if getattr(args, "mode", "run") == "run":
        results_dir = os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR", "/tmp")

        t = threading.Thread(target=test_runner_thread, args=(args, results_dir))
        t.daemon = True
        t.start()

    config.main(parser, get_config)
