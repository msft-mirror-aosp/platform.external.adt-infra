import argparse
import subprocess
import os
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
    parser.add_argument("--apk_dir", type=config.dir_type, help="Directory containing CTS verifier APKs")
    parser.add_argument("--build_tools_extract_dir", type=config.dir_type, help="Directory containing build tools")
    parser.add_argument("--script", help="Script to run")
    return parser

def get_config(ns: argparse.Namespace) -> list[test_sequencer_pb2.AgentConfig]:
    agents = [
        agent_common.goldfish_fetch(ns),
        agent_common.android_home(ns),
        agent_common.avd(ns),
        agent_common.goldfish(ns),
        agent_common.adb(ns, ["wait-for-device"]),
        agent_common.adb(ns, ["shell", "input", "keyevent", "82"]), # Unlock
    ]

    if hasattr(ns, 'apk_dir') and ns.apk_dir:
        main_apk = os.path.join(ns.apk_dir, "android-cts-verifier", "CtsVerifier.apk")
        # Block the sequence so it doesn't clean up the emulator while our python thread runs
        # We wait until the python thread touches /sdcard/verifier_done or /sdcard/verifier_failed
        agents.append(agent_common.adb(ns, ["shell", "rm -f /sdcard/verifier_done /sdcard/verifier_failed && while [ ! -f /sdcard/verifier_done ] && [ ! -f /sdcard/verifier_failed ]; do sleep 2; done; if [ -f /sdcard/verifier_failed ]; then exit 1; fi"], timeout_seconds=1200))

    return agents

def test_runner_thread(args, results_dir):
    try:
        runfiles = Runfiles.Create()

        adb_path = runfiles.Rlocation("platform-tools-linux/platform-tools/adb")
        if not adb_path or not os.path.exists(adb_path):
            adb_path = runfiles.Rlocation("_main/external/platform-tools-linux/platform-tools/adb")

        script_name = getattr(args, "script", "run_all_vibrations_tests.sh")
        if not script_name:
            script_name = "run_all_vibrations_tests.sh"

        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verifier", script_name)

        print(f"Waiting for adb binary at {adb_path}...")
        while not os.path.exists(adb_path):
            time.sleep(1)

        print(f"Found adb at {adb_path}")

        # Wait for emulator to fully boot
        print("Waiting for device...")
        subprocess.run([adb_path, "wait-for-device"], timeout=120)

        print("Waiting for sys.boot_completed...")
        while True:
            res = subprocess.run([adb_path, "shell", "getprop", "sys.boot_completed"], capture_output=True, text=True)
            if res.stdout.strip() == "1":
                break
            time.sleep(2)

        print("Waiting for package manager...")
        while True:
            res = subprocess.run([adb_path, "shell", "pm", "path", "android"], capture_output=True, text=True)
            if "package:" in res.stdout:
                break
            time.sleep(2)

        time.sleep(5)

        # Setup environment for the script
        env = os.environ.copy()

        # Symlink python3 to sys.executable
        bin_dir = os.path.join(results_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        python3_link = os.path.join(bin_dir, "python3")
        if not os.path.exists(python3_link):
            os.symlink(sys.executable, python3_link)

        env["PATH"] = bin_dir + os.pathsep + os.path.dirname(adb_path) + os.pathsep + env.get("PATH", "")
        env["PYTHONPATH"] = os.path.dirname(script_path) + os.pathsep + env.get("PYTHONPATH", "")
        if hasattr(args, 'apk_dir') and args.apk_dir:
            env["CTS_APK_PATH"] = os.path.join(args.apk_dir, "android-cts-verifier", "CtsVerifier.apk")
        env["CTS_OUTPUT_DIR"] = results_dir

        log_file = os.path.join(results_dir, "script_run.log")
        print(f"Executing bash script: {script_path}, logging to {log_file}")
        with open(log_file, "w") as f:
            p = subprocess.run(["bash", script_path], env=env, stdout=f, stderr=subprocess.STDOUT)

        print(f"Script finished with exit code {p.returncode}")
        with open(log_file, "r") as f:
            print(f"Script output:\n{f.read()}")

        # Unblock test_seq
        if p.returncode != 0:
            print("Script failed! Creating failure marker.")
            subprocess.run([adb_path, "shell", "touch", "/sdcard/verifier_failed"])
        else:
            print("Unblocking test_seq cleanup...")
            subprocess.run([adb_path, "shell", "touch", "/sdcard/verifier_done"])

    except Exception as e:
        print(f"Exception in test_runner_thread: {e}")
        subprocess.run([adb_path, "shell", "touch", "/sdcard/verifier_failed"])

if __name__ == "__main__":
    parser = get_parser()
    args, _ = parser.parse_known_args()

    if getattr(args, "mode", "run") == "run":
        results_dir = os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR", "/tmp")

        t = threading.Thread(target=test_runner_thread, args=(args, results_dir))
        t.daemon = True
        t.start()

    config.main(parser, get_config)
