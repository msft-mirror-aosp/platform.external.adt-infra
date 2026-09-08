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
            agent_common.goldfish(ns, id="goldfish_dut", avd_id="avd_dut"),
            agent_common.goldfish(ns, id="goldfish_companion", avd_id="avd_companion"),
        ]
        completion_target = "goldfish_dut"
    else:
        agents = [
            agent_common.goldfish_fetch(ns),
            agent_common.android_home(ns),
            agent_common.avd(ns),
            agent_common.goldfish(ns),
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
                timeout_seconds=540,
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

        multi_device = getattr(args, "multi_device", False)
        dev_mode = getattr(args, "dev_mode", False)
        required_count = 2 if multi_device else 1

        def get_connected_devices():
            res = subprocess.run([adb_path, "devices"], capture_output=True, text=True)
            devices = []
            for line in res.stdout.strip().splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    devices.append(parts[0])
            return devices

        print(f"Waiting for {required_count} device(s) to attach to adb...")
        while True:
            connected = get_connected_devices()
            if len(connected) >= required_count:
                break
            time.sleep(1)

        dut_serial = None
        companion_serial = None

        if multi_device:
            # Check results_dir for export files generated by test_seq goldfish agents
            try:
                for fname in os.listdir(results_dir):
                    if "goldfish_dut.export.txtpb" in fname:
                        with open(os.path.join(results_dir, fname)) as f:
                            for line in f:
                                if "serial_number:" in line:
                                    dut_serial = line.split('"')[1]
                    elif "goldfish_companion.export.txtpb" in fname:
                        with open(os.path.join(results_dir, fname)) as f:
                            for line in f:
                                if "serial_number:" in line:
                                    companion_serial = line.split('"')[1]
            except Exception:
                pass

        if not dut_serial:
            dut_serial = connected[0]
        if multi_device and not companion_serial:
            companion_serial = connected[1] if len(connected) > 1 else connected[0]

        print(f"Discovered devices: DUT={dut_serial}, Companion={companion_serial}")

        for dev_serial in (
            [dut_serial, companion_serial] if multi_device else [dut_serial]
        ):
            serial_prefix = ["-s", dev_serial]
            print(f"Waiting for sys.boot_completed on {dev_serial}...")
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

            print(f"Waiting for package manager on {dev_serial}...")
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
            env["DUT_SERIAL"] = dut_serial
            env["COMPANION_SERIAL"] = companion_serial
            env["CTS_DUT_SERIAL"] = dut_serial
            env["CTS_COMPANION_SERIAL"] = companion_serial
        else:
            env["DUT_SERIAL"] = dut_serial
            env["CTS_DUT_SERIAL"] = dut_serial

        env["ANDROID_SERIAL"] = dut_serial

        # Create launcher wrapper for python3 instead of symlink to avoid dangling link issues in Bazel sandbox
        bin_dir = os.path.join(results_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        python3_wrapper = os.path.join(bin_dir, "python3")
        with open(python3_wrapper, "w") as f:
            f.write(f'#!/usr/bin/env bash\nexec "{sys.executable}" "$@"\n')
        os.chmod(python3_wrapper, 0o755)

        xts_dir = os.path.dirname(os.path.abspath(__file__))
        goldfish_test_dir = os.path.dirname(xts_dir)
        verifier_dir = os.path.join(xts_dir, "verifier")

        env["PATH"] = (
            bin_dir
            + os.pathsep
            + os.path.dirname(adb_path)
            + os.pathsep
            + env.get("PATH", "")
        )
        env["PYTHONPATH"] = (
            verifier_dir
            + os.pathsep
            + xts_dir
            + os.pathsep
            + goldfish_test_dir
            + os.pathsep
            + env.get("PYTHONPATH", "")
        )
        if hasattr(args, "apk_dir") and args.apk_dir:
            env["CTS_APK_PATH"] = os.path.join(
                args.apk_dir, "android-cts-verifier", "CtsVerifier.apk"
            )
        env["CTS_OUTPUT_DIR"] = results_dir

        if dev_mode or getattr(args, "collect_tests", False):
            # In Dev mode, execute the TestBuilder directly to observe the live UI
            builder_script = os.path.join(
                verifier_dir, "automation_dev", "test_builder.py"
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
                raw_subname = os.environ.get(
                    "CTS_VERIFIER_SUBNAME",
                    os.path.basename(script_path)
                    .replace("run_", "")
                    .replace(".sh", ""),
                )
                # Normalize subname (e.g. 'camera_its' -> 'Camera Its', 'audio_loopback' -> 'Audio Loopback')
                if raw_subname in CTS_TEST_NAME_MAP:
                    test_subname = CTS_TEST_NAME_MAP[raw_subname]
                    print(
                        f"🛠️  Development Mode Active: Mapped '{raw_subname}' to exact test title: '{test_subname}'"
                    )
                    dev_cmd = [
                        sys.executable,
                        builder_script,
                        "--exact-test",
                        test_subname,
                    ]
                else:
                    raw_subname = (
                        raw_subname.replace("cts_verifier_", "")
                        .replace("cts-verifier.", "")
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
        if p.returncode != 0:
            print("Script failed! Creating failure marker.")
            for dev in connected:
                subprocess.run(
                    [adb_path, "-s", dev, "shell", "touch", "/sdcard/verifier_failed"],
                    check=False,
                )
        else:
            print("Unblocking test_seq cleanup...")
            for dev in connected:
                subprocess.run(
                    [adb_path, "-s", dev, "shell", "touch", "/sdcard/verifier_done"],
                    check=False,
                )

    except Exception as e:
        print(f"Exception in test_runner_thread: {e}")
        for dev in get_connected_devices() or [""]:
            prefix = ["-s", dev] if dev else []
            subprocess.run(
                [adb_path] + prefix + ["shell", "touch", "/sdcard/verifier_failed"],
                check=False,
            )


if __name__ == "__main__":
    parser = get_parser()
    args, _ = parser.parse_known_args()

    is_print_mode = "--mode=print" in sys.argv or (
        "--mode" in sys.argv and "print" in sys.argv
    )

    if not is_print_mode:
        results_dir = os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR", "/tmp")

        t = threading.Thread(target=test_runner_thread, args=(args, results_dir))
        t.daemon = True
        t.start()

    config.main(parser, get_config)
