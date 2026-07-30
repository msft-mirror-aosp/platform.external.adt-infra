#!/usr/bin/env python3
import sys
import time
import os

import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)
from cts_common import adb, ui_dump, tap, find_node

def remove_fingerprint(finger_id):
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
    else:
        print("Fingerprint menu not found. It might already be disabled.")
        return

    root = ui_dump()
    if find_node(root, text="Enter your device PIN") is not None or find_node(root, text="Re-enter your PIN") is not None:
        print("Entering PIN...")
        adb("shell", "input", "text", "1111")
        time.sleep(1)
        adb("shell", "input", "keyevent", "KEYCODE_ENTER")
        time.sleep(3)

    print(f"Checking for Finger {finger_id}...")
    root = ui_dump()
    del_btn = find_node(root, content_desc=f"Delete Finger {finger_id}")
    
    if del_btn is None:
        # Sometimes the content desc might just be 'Delete' if it's not strictly 'Delete Finger X' 
        # But based on our dump, it is 'Delete Finger 1'
        print(f"Fingerprint {finger_id} not found.")
        return

    print(f"Tapping Delete for Finger {finger_id}...")
    tap(del_btn)
    time.sleep(2)
    
    print("Confirming Delete...")
    root = ui_dump()
    confirm_btn = find_node(root, text="Delete")
    if confirm_btn is not None:
        tap(confirm_btn)
        time.sleep(2)
        print(f"Fingerprint {finger_id} removed successfully.")
    else:
        print("Could not find confirmation Delete button.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <fingerid>")
        sys.exit(1)
    
    finger_id = sys.argv[1]
    remove_fingerprint(finger_id)
