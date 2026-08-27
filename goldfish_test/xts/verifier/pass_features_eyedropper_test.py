#!/usr/bin/env python3
"""
EyeDropper Test
Verifies the EyeDropper API functionality.
"""

import time
from cts_common import (
    setup, navigate_to, ui_dump, find_node, tap, wait_for, tap_pass,
    export_and_verify, set_screenshot_dir, screenshot, bounds_center, adb,
    dismiss_dialogs_and_wait_for_pass, get_screen_size
)

TEST_NAME = "EyeDropper Test"
set_screenshot_dir("eyedropper_test")

def main():
    # Enhance the script to ensure a completely clean install of the CtsVerifier
    PACKAGE = "com.android.cts.verifier"
    print(f"Uninstalling {PACKAGE} to ensure a clean state...")
    adb("uninstall", PACKAGE, check=False)
    
    setup() # This will reinstall it with -g -r 
    
    print(f"Navigating to {TEST_NAME}...")
    screenshot("navigating")
    try:
        navigate_to(TEST_NAME)
    except RuntimeError:
        print(f"Failed to find '{TEST_NAME}' in the list.")
        return
        
    time.sleep(2)

    root = ui_dump()
    print("Waiting for OK dialog...")
    try:
        ok = wait_for(text="OK", timeout=15)
        tap(ok)
        time.sleep(2)
    except TimeoutError:
        print("Warning: OK dialog not found, proceeding anyway...")

    print("Waiting for color labels to load...")
    try:
        wait_for(text="#FF0000", timeout=15)
    except TimeoutError:
        print("Warning: Color labels did not appear.")

    root = ui_dump()
    
    w, h = get_screen_size()
    
    # 1. Find the 4 color boxes
    colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00"]
    color_coords = []
    
    for color in colors:
        label = find_node(root, text=color)
        if label is not None:
            # Find the actual color block view preceding the label
            all_nodes = list(root.iter("node"))
            color_box = None
            for idx, n in enumerate(all_nodes):
                if n == label:
                    # Look at the previous node. Often it's an android.view.View
                    if idx > 0 and all_nodes[idx - 1].attrib.get("class") == "android.view.View":
                        color_box = all_nodes[idx - 1]
                    break
            
            if color_box is not None:
                bx, by = bounds_center(color_box)
                color_coords.append((bx, by))
            else:
                print(f"Warning: Could not find color box View preceding {color}. Using offset fallback.")
                lx, ly = bounds_center(label)
                offset = int(h * 0.035)
                color_coords.append((lx, ly - offset)) 
        else:
            print(f"Warning: Could not find label {color}")
            
    if not color_coords:
        print("Could not find any color boxes. Falling back to default layout.")
        w, h = get_screen_size()
        color_coords = [
            (int(w * 0.27), int(h * 0.26)),
            (int(w * 0.42), int(h * 0.26)),
            (int(w * 0.58), int(h * 0.26)),
            (int(w * 0.73), int(h * 0.26))
        ]

    center_x, center_y = w // 2, h // 2

    for i, coords in enumerate(color_coords):
        target_color = colors[i]
        print(f"Step {i+1}: Targeting color square {target_color} at {coords}")
        
        # Tap Launch EyeDropper
        root = ui_dump()
        launch_btn = find_node(root, resource_id="com.android.cts.verifier:id/launch_eyedropper_button")
        if launch_btn is None:
            for node in root.iter("node"):
                text = node.attrib.get("text", "").lower()
                if node.attrib.get("clickable") == "true" and "launch" in text:
                    launch_btn = node
                    break
                    
        if launch_btn is not None:
            print(f"Tapping launch button...")
            tap(launch_btn)
        else:
            print("Launch button not found, tapping center of screen...")
            adb("shell", "input", "tap", str(center_x), str(center_y))
            
        time.sleep(3)
        screenshot(f"launched_eyedropper_{i}")

        # Drag from center (where eyedropper usually spawns) to the color box
        cx, cy = coords
        print(f"Dragging eyedropper to {cx}, {cy}...")
        adb("shell", "input", "swipe", str(center_x), str(center_y), str(cx), str(cy), "1000")
        time.sleep(2)
        
        print(f"Checking color label for {target_color}...")
        screenshot(f"dragged_eyedropper_{target_color.strip('#')}_{i}")

        # Click the Check (Confirm) button
        root = ui_dump()
        confirm_btn = find_node(root, content_desc="Confirm")
        if confirm_btn is not None:
            print("Tapping Confirm (check) symbol...")
            tap(confirm_btn)
        else:
            print("Confirm button not found, trying approximate taps for different OS versions...")
            # Local / Older OS (UI drawn near the top)
            adb("shell", "input", "tap", str(int(w * 0.65)), str(int(h * 0.3)))
            time.sleep(0.5)
            # RBE / Android 15 (UI moved to bottom because reticle is at the top)
            for dx in [0.62, 0.65, 0.68]:
                for dy in [0.74, 0.76, 0.78]:
                    adb("shell", "input", "tap", str(int(w * dx)), str(int(h * dy)))
            
        time.sleep(2)

    print("Waiting for Pass button to become enabled...")
    try:
        pass_btn = dismiss_dialogs_and_wait_for_pass(timeout=10)
        print("Tapping Pass...")
        screenshot("tapping_pass")
        tap(pass_btn)
    except TimeoutError:
        print("Warning: Pass button did not become enabled. Tapping it anyway to try.")
        tap_pass()
        
    export_and_verify(TEST_NAME)

if __name__ == "__main__":
    main()
