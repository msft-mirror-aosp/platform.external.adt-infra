#!/usr/bin/env python3
import sys
import subprocess
import time
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)
from cts_common import adb, ui_dump, tap, find_node, screenshot, set_screenshot_dir

def wait_for_node_with_text(texts, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        for t in texts:
            node = find_node(root, text=t)
            if node is not None:
                return root, node
        time.sleep(2)
    return None, None

def wait_for_node(text, timeout=30):
    return wait_for_node_with_text([text], timeout=timeout)

def wait_for_cpu_load(threshold=50.0, timeout=120):
    print(f"Waiting for CPU load to drop below {threshold}% (out of 400%)...")

    def read_stat():
        out = adb("shell", "cat", "/proc/stat", check=False)
        for line in out.splitlines():
            if line.startswith("cpu "):
                parts = line.split()[1:]
                idle = int(parts[3])
                if len(parts) > 4:
                    idle += int(parts[4])
                total = sum(int(p) for p in parts)
                return idle, total
        return 0, 0

    deadline = time.time() + timeout
    while time.time() < deadline:
        idle1, total1 = read_stat()
        time.sleep(1)
        idle2, total2 = read_stat()

        idle_delta = idle2 - idle1
        total_delta = total2 - total1

        if total_delta > 0:
            usage = ((total_delta - idle_delta) / total_delta) * 400.0
            print(f"Current CPU load: {usage:.1f}%")
            if usage < threshold:
                print(f"CPU load is below threshold ({threshold}%). Proceeding...")
                return
        else:
            print("Failed to read CPU load.")
            time.sleep(2)

    print("Warning: Timed out waiting for CPU load to drop.")

def enroll_fingerprint(finger_id):
    set_screenshot_dir(f"enroll_fingerprint_{finger_id}")

    # Ensure PIN is set first
    print("Ensuring PIN 1111 is set...")
    subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "create_pin.py"), "1111"], check=True)
    screenshot("01_after_create_pin")

    wait_for_cpu_load(threshold=50.0, timeout=120)

    print("Opening Security Settings...")
    adb("shell", "am", "force-stop", "com.android.settings")
    adb("shell", "am", "start", "-a", "android.settings.SECURITY_SETTINGS")

    print("Waiting for Security settings to load...")
    deadline = time.time() + 30
    du_btn = None
    while time.time() < deadline:
        root = ui_dump()
        du_btn = find_node(root, text="Device unlock")
        if du_btn is not None:
            break
        # Swipe in case we need to scroll down
        adb("shell", "input", "swipe", "540", "1500", "540", "500", "300")
        time.sleep(2)

    if du_btn is None:
        screenshot("failed_device_unlock")
        raise RuntimeError("Failed to find Device unlock")

    screenshot("02_security_settings")

    print("Navigating to Device unlock...")
    tap(du_btn)

    print("Waiting for Fingerprint menu...")
    fp_texts = ["Fingerprint", "Face & Fingerprint Unlock", "Fingerprint Unlock"]
    root, fp_btn = wait_for_node_with_text(fp_texts, timeout=30)

    if fp_btn is None:
        screenshot("failed_fingerprint_menu")
        raise RuntimeError("Failed to find Fingerprint menu")

    screenshot("03_device_unlock")

    print("Navigating to Fingerprint...")
    tap(fp_btn)

    # Wait to see if it asks for PIN or goes directly to Add / setup
    time.sleep(2)
    screenshot("04_fingerprint_menu")

    print("Navigating through fingerprint setup state machine...")
    enroll_success = False
    has_tapped_add = False
    for i in range(60): # Increased loop range just in case
        root = ui_dump()

        # Check for PIN prompt
        if find_node(root, text="Enter your device PIN") is not None or find_node(root, text="Re-enter your PIN") is not None:
            print("Entering PIN...")
            screenshot(f"pin_prompt_{i}")
            adb("shell", "input", "text", "1111")
            time.sleep(1)
            adb("shell", "input", "keyevent", "KEYCODE_ENTER")
            # Wait for PIN processing
            time.sleep(3)
            screenshot(f"after_pin_prompt_{i}")
            continue

        # Check for Add
        add_btn = find_node(root, text="Add") or find_node(root, text="Add fingerprint")
        if add_btn is not None:
            if not has_tapped_add:
                print("Tapping Add...")
                screenshot(f"add_fingerprint_{i}")
                tap(add_btn)
                has_tapped_add = True
                time.sleep(3)
                screenshot(f"after_add_fingerprint_{i}")
            continue

        # Check for MORE
        more_btn = find_node(root, text="MORE")
        if more_btn is not None:
            print("Tapping MORE...")
            screenshot(f"more_{i}")
            tap(more_btn)
            time.sleep(2)
            screenshot(f"after_more_{i}")
            continue

        # Check for I AGREE
        agree_btn = find_node(root, text="I AGREE")
        if agree_btn is not None:
            print("Tapping I AGREE...")
            screenshot(f"i_agree_{i}")
            tap(agree_btn)
            time.sleep(2)
            screenshot(f"after_i_agree_{i}")
            continue

        # Check for ANR
        wait_btn = find_node(root, text="Wait")
        if wait_btn is not None:
            print("Settings is ANRing! Tapping 'Wait'...")
            screenshot(f"anr_wait_{i}")
            tap(wait_btn)
            time.sleep(2)
            continue

        # Check for DONE
        done_btn = find_node(root, text="DONE")
        if done_btn is not None:
            print("Tapping DONE...")
            screenshot(f"done_{i}")
            tap(done_btn)
            time.sleep(2)
            enroll_success = True
            break

        # Check if we are on the Touch screen
        text_nodes = [n.attrib.get("text", "").lower() for n in root.iter("node")]
        if any("touch" in t or "sensor" in t for t in text_nodes):
            print(f"On enrollment screen (touch {i}). Simulating touch...")
            screenshot(f"enroll_touch_{i}")

            if not getattr(enroll_fingerprint, "help_printed", False):
                print("Dumping input devices:")
                print(adb("shell", "getevent", "-il", check=False))
                enroll_fingerprint.help_printed = True

            out = adb("emu", "finger", "touch", str(finger_id), check=False)
            if i == 4 or i == 5:
                print(f"adb emu finger touch output: '{out}'")

            # If emu finger touch fails, fail the enrollment
            if "KO" in out or "unknown" in out.lower() or "not found" in out.lower() or out.strip() == "":
                screenshot("failed_emu_finger_touch")
                raise RuntimeError(f"adb emu finger touch failed with output: '{out}'")

            time.sleep(1.5)
            screenshot(f"after_enroll_touch_{i}")
            continue

        # Otherwise wait
        time.sleep(1)

    if not enroll_success:
        import xml.etree.ElementTree as ET
        print("Failed to find DONE button. UI dump:")
        print(ET.tostring(ui_dump(), encoding='unicode'))
        screenshot("failed_done_not_found")
        raise RuntimeError(f"Fingerprint {finger_id} enrollment failed - DONE button never appeared.")

    print(f"Fingerprint {finger_id} enrollment completed.")
    screenshot("enrollment_completed")

    print("Swiping away Settings app...")
    # Open Recents
    adb("shell", "input", "keyevent", "KEYCODE_APP_SWITCH")
    time.sleep(1.5)
    # Swipe up to clear the app
    adb("shell", "input", "swipe", "540", "1500", "540", "100", "300")
    time.sleep(1)
    # Go back to Home
    adb("shell", "input", "keyevent", "KEYCODE_HOME")

    # Also force-stop just to be sure it doesn't linger in a broken state
    adb("shell", "am", "force-stop", "com.android.settings")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <fingerid>")
        sys.exit(1)

    finger_id = sys.argv[1]
    enroll_fingerprint(finger_id)
