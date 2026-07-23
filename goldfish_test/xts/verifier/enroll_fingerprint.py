#!/usr/bin/env python3
import sys
import subprocess
import time
import os

import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)
from cts_common import adb, ui_dump, tap, find_node

def enroll_fingerprint(finger_id):
    # Ensure PIN is set first
    print("Ensuring PIN 1111 is set...")
    subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "create_pin.py"), "1111"], check=True)

    print("Opening Security Settings...")
    adb("shell", "am", "force-stop", "com.android.settings")
    adb("shell", "am", "start", "-a", "android.settings.SECURITY_SETTINGS")
    time.sleep(3)

    print("Navigating to Device unlock...")
    root = ui_dump()
    du_btn = find_node(root, text="Device unlock")
    if du_btn is not None:
        tap(du_btn)
        time.sleep(2)
    else:
        adb("shell", "input", "swipe", "540", "1500", "540", "500", "300")
        time.sleep(2)
        root = ui_dump()
        du_btn = find_node(root, text="Device unlock")
        if du_btn is not None:
            tap(du_btn)
            time.sleep(2)

    print("Navigating to Fingerprint...")
    root = ui_dump()
    fp_btn = find_node(root, text="Fingerprint")
    if fp_btn is not None:
        tap(fp_btn)
        time.sleep(2)

    root = ui_dump()
    if find_node(root, text="Enter your device PIN") is not None or find_node(root, text="Re-enter your PIN") is not None:
        print("Entering PIN...")
        adb("shell", "input", "text", "1111")
        time.sleep(1)
        adb("shell", "input", "keyevent", "KEYCODE_ENTER")
        time.sleep(3)

    root = ui_dump()
    # Check if we are on the fingerprint list page and need to click "Add" or "Add fingerprint"
    add_btn = find_node(root, text="Add")
    if add_btn is None:
        add_btn = find_node(root, text="Add fingerprint")
        
    if add_btn is not None:
        print("Tapping Add...")
        tap(add_btn)
        time.sleep(2)

    # We might have "MORE" and "I AGREE" prompts
    for _ in range(3):
        root = ui_dump()
        
        # If we reached the enrollment screen, we can break early
        if find_node(root, text="Touch the sensor") is not None or find_node(root, text="Lift, then touch again") is not None:
            break
            
        more_btn = find_node(root, text="MORE")
        if more_btn is not None:
            print("Tapping MORE...")
            tap(more_btn)
            time.sleep(2)
        
        root = ui_dump()
        agree_btn = find_node(root, text="I AGREE")
        if agree_btn is not None:
            print("Tapping I AGREE...")
            tap(agree_btn)
            time.sleep(2)
            break
        
        time.sleep(1)

    # Touch sensor loop
    root = ui_dump()
    if find_node(root, text="Touch the sensor") is not None or find_node(root, text="Lift, then touch again") is not None or find_node(root, text="DO IT LATER") is not None:
        print("Enrolling fingerprint by touching sensor...")
        for i in range(15):
            root = ui_dump()
            done_btn = find_node(root, text="DONE")
            if done_btn is not None:
                print("Tapping DONE...")
                tap(done_btn)
                time.sleep(2)
                break
            
            # Send touch
            adb("emu", "finger", "touch", str(finger_id))
            time.sleep(1.5)
            
    print(f"Fingerprint {finger_id} enrollment completed.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <fingerid>")
        sys.exit(1)
    
    finger_id = sys.argv[1]
    enroll_fingerprint(finger_id)
