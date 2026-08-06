#!/usr/bin/env python3
"""
CtsVerifier Test Builder & Automation Development Tool.

Location: xts/verifier/automation_dev/test_builder.py

This tool helps engineers and agents build robust CtsVerifier test automation scripts:
1. Performs setup and navigates to the target test.
2. Captures screenshots and UI XML dumps at every state transition.
3. Displays an interactive menu of clickable elements or accepts manual input commands.
4. Records every action into a clean, auto-generated Python test script.
5. If stuck or an unexpected dialog appears, pings the user for guidance!
"""

import argparse
import json
import os
import re
import select
import sys
import time
import xml.etree.ElementTree as ET


def read_command_input(prompt="\nTestBuilder> "):
    """Read input line or raw bytes from user or background task non-blockingly."""
    print(prompt, end="", flush=True)
    if not sys.stdin.isatty():
        # Non-interactive / pipe mode (e.g., manage_task send_input)
        while True:
            try:
                rlist, _, _ = select.select([sys.stdin.fileno()], [], [], 0.5)
                if rlist:
                    raw_bytes = os.read(sys.stdin.fileno(), 1024)
                    if raw_bytes:
                        cmd = raw_bytes.decode("utf-8", errors="ignore").strip()
                        if cmd:
                            print(f"{cmd}")
                            return cmd
            except Exception as e:
                print(f"Read error: {e}")
                break
            time.sleep(0.2)
    return input().strip()


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VERIFIER_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.append(VERIFIER_DIR)

from cts_common import (
    adb,
    setup,
    navigate_to,
    ui_dump,
    find_node,
    tap,
    tap_pass,
    screenshot,
    set_screenshot_dir,
    export_and_verify,
    SERIAL,
    enable_adb_trace,
    get_adb_trace_log,
    install_empty_device_admin,
)


class TestBuilder:
    def __init__(self, test_name, output_script_path=None):
        self.test_name = test_name
        test_slug = re.sub(r"[^a-zA-Z0-9]+", "_", test_name).lower()
        self.output_script_path = output_script_path or os.path.join(
            VERIFIER_DIR, f"pass_{test_slug}_test.py"
        )
        self.step_count = 0
        self.recorded_steps = []
        self.session_dir = os.path.join(SCRIPT_DIR, "sessions", test_slug)
        os.makedirs(self.session_dir, exist_ok=True)
        set_screenshot_dir(self.session_dir)
        self.trace_file = os.path.join(self.session_dir, "session_trace.json")
        self.trace_data = []

    def get_device_system_state(self):
        """Query activity, power interactive state, and Keyguard status."""
        act_res = adb("shell", "dumpsys", "window", check=False)
        curr_act = "UnknownActivity"
        match = re.search(r"mCurrentFocus=Window\{[^\}]*\s+(\S+)\}", act_res)
        if match:
            curr_act = match.group(1)

        power_res = adb("shell", "dumpsys", "power", check=False)
        is_interactive = (
            "mInteractive=true" in power_res or "Display Power: state=ON" in power_res
        )

        is_keyguard = (
            "StatusBar" in act_res
            or "NotificationShade" in act_res
            or "Keyguard" in act_res
            or "com.android.systemui" in curr_act
        )

        return {
            "activity": curr_act,
            "interactive": is_interactive,
            "keyguard_showing": is_keyguard,
        }

    def record_trace_step(
        self, pre_state, post_state, action_type, element_info=None, snapshot_xml=""
    ):
        state_delta = []
        if pre_state.get("activity") != post_state.get("activity"):
            state_delta.append(
                f"activity_changed: {pre_state.get('activity')} -> {post_state.get('activity')}"
            )
        if pre_state.get("interactive") and not post_state.get("interactive"):
            state_delta.append("screen_locked_off")
        elif not pre_state.get("interactive") and post_state.get("interactive"):
            state_delta.append("screen_woken_up")
        if not pre_state.get("keyguard_showing") and post_state.get("keyguard_showing"):
            state_delta.append("keyguard_prompt_opened")
        elif pre_state.get("keyguard_showing") and not post_state.get(
            "keyguard_showing"
        ):
            state_delta.append("keyguard_unlocked")

        step_record = {
            "step": self.step_count,
            "action": action_type,
            "pre_state": pre_state,
            "post_state": post_state,
            "state_delta": state_delta,
            "interacted_element": element_info or {},
            "resulting_snapshot": snapshot_xml,
        }
        self.trace_data.append(step_record)
        with open(self.trace_file, "w", encoding="utf-8") as tf:
            json.dump(self.trace_data, tf, indent=2)
        print(
            f" 📜 Trace logged to: {self.trace_file} | Delta: {', '.join(state_delta) or 'None'}"
        )

    def capture_snapshot(self, description=""):
        self.step_count += 1
        prefix = (
            f"{self.step_count:02d}_{re.sub(r'[^a-zA-Z0-9]+', '_', description).lower()}"
            if description
            else f"{self.step_count:02d}"
        )
        img_filename = f"{prefix}.png"
        xml_filename = f"{prefix}.xml"

        # Take screenshot
        screenshot_path = os.path.join(self.session_dir, img_filename)
        adb("shell", "screencap", "-p", f"/sdcard/{img_filename}")
        adb("pull", f"/sdcard/{img_filename}", screenshot_path)
        adb("shell", "rm", "-f", f"/sdcard/{img_filename}")

        # Dump UI XML
        root = ui_dump()
        xml_path = os.path.join(self.session_dir, xml_filename)
        ET.ElementTree(root).write(xml_path)

        return root, screenshot_path, xml_path

    def get_interactive_elements(self, root):
        elements = []
        for node in root.iter("node"):
            text = node.attrib.get("text", "").strip()
            content_desc = node.attrib.get("content-desc", "").strip()
            resource_id = node.attrib.get("resource-id", "").strip()
            clickable = node.attrib.get("clickable") == "true"
            enabled = node.attrib.get("enabled", "true") == "true"
            bounds = node.attrib.get("bounds", "")

            if (text or content_desc or resource_id) and (
                clickable
                or text
                in [
                    "OK",
                    "Cancel",
                    "Allow",
                    "Deny",
                    "Force Lock",
                    "Generate Policy",
                    "Apply Policy",
                    "Uninstall",
                    "Uninstall app",
                    "Archive",
                    "Force stop",
                    "Launch settings",
                    "Enable admin",
                ]
            ):
                elements.append(
                    {
                        "node": node,
                        "text": text,
                        "content_desc": content_desc,
                        "resource_id": resource_id,
                        "clickable": clickable,
                        "enabled": enabled,
                        "bounds": bounds,
                    }
                )
        return elements

    def print_menu(self, elements, current_activity=""):
        print("\n" + "=" * 70)
        print(f" 📍 STEP {self.step_count:02d} | Activity: {current_activity}")
        print("=" * 70)
        print(" Interactive Elements Found:")
        for idx, el in enumerate(elements, 1):
            label_parts = []
            if el["text"]:
                label_parts.append(f'text="{el["text"]}"')
            if el["content_desc"]:
                label_parts.append(f'content_desc="{el["content_desc"]}"')
            if el["resource_id"]:
                res_short = el["resource_id"].split("/")[-1]
                label_parts.append(f'id="{res_short}"')

            dis_str = " (DISABLED)" if not el["enabled"] else ""
            print(f"  [{idx:2d}] {' | '.join(label_parts)} {dis_str}")

        print("-" * 70)
        print(" Available TestBuilder Commands:")
        print("  <number>        : Tap element by number (e.g. '1')")
        print("  tap <text/id>   : Tap element by text or ID (e.g. 'tap Force Lock')")
        print("  swipe_up        : Swipe up to unlock or scroll")
        print(
            "  key <code/name> : Send key event (e.g. 'key 82' or 'key KEYCODE_WAKEUP')"
        )
        print("  reboot          : Reboot device and wait for reconnect")
        print("  sleep <sec>     : Insert delay (e.g. 'sleep 2')")
        print("  pass            : Tap Pass button and complete test recording")
        print("  ping <msg>      : Ping user for guidance/help if stuck!")
        print("=" * 70)

    def record_step(self, python_code_line, comment=""):
        if comment:
            self.recorded_steps.append(f"# {comment}")
        self.recorded_steps.append(python_code_line)
        print(f" 📝 Recorded: {python_code_line}")

    def run_interactive(self):
        print(f"\n🚀 Starting TestBuilder for: '{self.test_name}'...")
        enable_adb_trace(True)
        setup()
        root, img, xml = self.capture_snapshot("app_launched")

        print(f"Navigating to '{self.test_name}'...")
        navigate_to(self.test_name)
        time.sleep(2)
        root, img, xml = self.capture_snapshot("test_opened")

        while True:
            pre_state = self.get_device_system_state()
            curr_act = pre_state["activity"]

            elements = self.get_interactive_elements(root)
            self.print_menu(elements, curr_act)

            try:
                cmd_raw = read_command_input()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting TestBuilder.")
                break

            if not cmd_raw:
                continue

            if cmd_raw.isdigit():
                idx = int(cmd_raw) - 1
                if 0 <= idx < len(elements):
                    el = elements[idx]
                    print(
                        f"Tapping element #{idx + 1}: {el['text'] or el['content_desc'] or el['resource_id']}..."
                    )
                    tap(el["node"])
                    el_info = {
                        "text": el["text"],
                        "content_desc": el["content_desc"],
                        "resource_id": el["resource_id"],
                        "class": el["node"].attrib.get("class", ""),
                        "package": el["node"].attrib.get("package", ""),
                        "bounds": el["bounds"],
                    }
                    if el["text"]:
                        self.record_step(
                            f'node = wait_for(text="{el["text"]}", timeout=15)\ntap(node)',
                            f'Wait for and tap "{el["text"]}"',
                        )
                    elif el["content_desc"]:
                        self.record_step(
                            f'node = wait_for(content_desc="{el["content_desc"]}", timeout=15)\ntap(node)',
                            f'Wait for and tap "{el["content_desc"]}"',
                        )
                    elif el["resource_id"]:
                        self.record_step(
                            f'node = wait_for(resource_id="{el["resource_id"]}", timeout=15)\ntap(node)',
                            f'Wait for and tap "{el["resource_id"]}"',
                        )
                    time.sleep(2)
                    root, img, xml = self.capture_snapshot(
                        el["text"] or el["content_desc"] or "tapped"
                    )
                    post_state = self.get_device_system_state()
                    self.record_trace_step(
                        pre_state,
                        post_state,
                        "tap_element",
                        el_info,
                        os.path.basename(xml),
                    )
                else:
                    print(f"Invalid element index {cmd_raw}!")
            elif cmd_raw.startswith("tap "):
                target = cmd_raw[4:].strip().strip("\"'")
                node = find_node(root, text=target) or find_node(
                    root, content_desc=target
                )
                if node is None:
                    # Partial / containing search fallback
                    for n in root.iter("node"):
                        if (
                            target.lower() in n.attrib.get("text", "").lower()
                            or target.lower()
                            in n.attrib.get("content-desc", "").lower()
                            or target.lower() in n.attrib.get("resource-id", "").lower()
                        ):
                            node = n
                            break
                if node is not None:
                    print(f"Tapping '{target}'...")
                    el_info = {
                        "text": node.attrib.get("text", "").strip(),
                        "content_desc": node.attrib.get("content-desc", "").strip(),
                        "resource_id": node.attrib.get("resource-id", "").strip(),
                        "class": node.attrib.get("class", ""),
                        "package": node.attrib.get("package", ""),
                        "bounds": node.attrib.get("bounds", ""),
                    }
                    tap(node)
                    self.record_step(
                        f'node = wait_for(text="{target}", timeout=15)\ntap(node)',
                        f'Wait for and tap "{target}"',
                    )
                    time.sleep(2)
                    root, img, xml = self.capture_snapshot(target)
                    post_state = self.get_device_system_state()
                    self.record_trace_step(
                        pre_state,
                        post_state,
                        "tap_text",
                        el_info,
                        os.path.basename(xml),
                    )
                else:
                    print(f"Could not find element matching '{target}'!")
            elif cmd_raw.startswith("text "):
                txt_input = cmd_raw[5:].strip()
                print(f"Entering text '{txt_input}'...")
                adb("shell", "input", "text", txt_input)
                self.record_step(
                    f'adb("shell", "input", "text", "{txt_input}")',
                    f'Input text "{txt_input}"',
                )
                time.sleep(1)
                root, img, xml = self.capture_snapshot(f"text_{txt_input}")
                post_state = self.get_device_system_state()
                self.record_trace_step(
                    pre_state,
                    post_state,
                    "input_text",
                    {"text": txt_input},
                    os.path.basename(xml),
                )
            elif cmd_raw == "swipe_up":
                print("Swiping up...")
                adb("shell", "input", "swipe", "720", "2500", "720", "500", "300")
                self.record_step(
                    'adb("shell", "input", "swipe", "720", "2500", "720", "500", "300")',
                    "Swipe up to unlock/scroll",
                )
                time.sleep(2)
                root, img, xml = self.capture_snapshot("swipe_up")
                post_state = self.get_device_system_state()
                self.record_trace_step(
                    pre_state, post_state, "swipe_up", {}, os.path.basename(xml)
                )
            elif cmd_raw.startswith("key "):
                kcode = cmd_raw[4:].strip()
                print(f"Sending keyevent {kcode}...")
                adb("shell", "input", "keyevent", kcode)
                if kcode == "82" or kcode == "KEYCODE_WAKEUP":
                    self.record_step(
                        f'adb("shell", "input", "keyevent", "{kcode}")\nwait_for_keyguard_showing()',
                        f"Wake screen and wait for Keyguard prompt",
                    )
                else:
                    self.record_step(
                        f'adb("shell", "input", "keyevent", "{kcode}")',
                        f"Key event {kcode}",
                    )
                time.sleep(2)
                root, img, xml = self.capture_snapshot(f"key_{kcode}")
                post_state = self.get_device_system_state()
                self.record_trace_step(
                    pre_state,
                    post_state,
                    f"keyevent_{kcode}",
                    {"keycode": kcode},
                    os.path.basename(xml),
                )
            elif cmd_raw == "reboot":
                print("Rebooting device...")
                from cts_common import reboot_and_wait

                reboot_and_wait()
                self.record_step(
                    "reboot_and_wait()", "Reboot and wait for boot complete"
                )
                root, img, xml = self.capture_snapshot("post_reboot")
                post_state = self.get_device_system_state()
                self.record_trace_step(
                    pre_state, post_state, "reboot", {}, os.path.basename(xml)
                )
            elif cmd_raw.startswith("sleep "):
                secs = float(cmd_raw[6:].strip())
                print(f"Sleeping {secs}s...")
                time.sleep(secs)
                self.record_step(f"time.sleep({secs})", f"Wait {secs}s")
                post_state = self.get_device_system_state()
                self.record_trace_step(
                    pre_state, post_state, "sleep", {"duration": secs}, ""
                )
            elif cmd_raw.startswith("ping "):
                msg = cmd_raw[5:].strip()
                print(f"\n🔔 [AGENT PING TO USER]: {msg}")
                input("Press ENTER when you have unblocked/guided the state...")
                root, img, xml = self.capture_snapshot("after_user_guidance")
                post_state = self.get_device_system_state()
                self.record_trace_step(
                    pre_state,
                    post_state,
                    "user_ping",
                    {"message": msg},
                    os.path.basename(xml),
                )
            elif cmd_raw == "pass":
                post_state = self.get_device_system_state()
                self.record_trace_step(
                    pre_state,
                    post_state,
                    "pass",
                    {"content_desc": "Pass"},
                    "verifier_pass.xml",
                )
                print("Tapping Pass button and completing test...")
                pass_btn = find_node(root, content_desc="Pass") or find_node(
                    root, text="Pass"
                )
                if pass_btn is not None:
                    tap_pass(pass_btn)
                self.record_step(
                    """pass_btn = wait_for(content_desc="Pass", timeout=15)
tap_pass(pass_btn)
time.sleep(2)""",
                    "Wait for and tap Pass button",
                )

                print("Navigating back to main activity for export...")
                adb(
                    "shell",
                    "am",
                    "start",
                    "-n",
                    "com.android.cts.verifier/.CtsVerifierActivity",
                )
                self.record_step(
                    'adb("shell", "am", "start", "-n", "com.android.cts.verifier/.CtsVerifierActivity")\ntime.sleep(3)\nexport_and_verify(TEST_NAME)',
                    "Export test result",
                )
                break
            else:
                print(f"Unknown command: '{cmd_raw}'")

        self.generate_script()

    def generate_script(self):
        print(f"\n💾 Writing generated test script to: {self.output_script_path} ...")
        steps_code = "\n\n".join(self.recorded_steps)
        script_content = f'''#!/usr/bin/env python3
"""
Auto-generated pass test script for CtsVerifier test: {self.test_name}
Generated by automation_dev/test_builder.py
"""

import os
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from cts_common import (
    adb, setup, navigate_to, ui_dump, find_node, tap, tap_pass,
    screenshot, set_screenshot_dir, export_and_verify, reboot_and_wait,
    wait_for, wait_for_screen_off, wait_for_keyguard_showing,
    install_empty_device_admin
)

TEST_NAME = "{self.test_name}"

set_screenshot_dir("{re.sub(r'[^a-zA-Z0-9]+', '_', self.test_name).lower()}")

# Step 0: Setup & Launch
setup()
screenshot("app_launched")

# Step 1: Navigate to Test
navigate_to(TEST_NAME)
time.sleep(2)
screenshot("test_opened")

# Step 2: Recorded Test Actions
{steps_code}

print(f"Finished {self.test_name} successfully!")
'''
        with open(self.output_script_path, "w") as f:
            f.write(script_content)
        os.chmod(self.output_script_path, 0o755)
        print(f"✅ Generated test script successfully at: {self.output_script_path}")


def collect_test_module_names(output_json_path=None):
    """
    Launches CtsVerifier, dismisses initial dialogs, scrolls through the main list view,
    collects all test activity labels and categories, and writes them to a JSON file organized by Category and TestItem.
    """
    if not output_json_path:
        output_json_path = os.path.join(VERIFIER_DIR, "cts_verifier_test_labels.json")

    import json

    print("Starting CtsVerifier test label collection over ADB...")
    setup()
    time.sleep(3)

    collected_labels = set()
    categories = {}
    current_category = "GENERAL / UNCATEGORIZED"
    categories[current_category] = []
    no_new_count = 0
    max_swipes = 50

    for i in range(max_swipes):
        root = ui_dump()

        # Dismiss any permission / OK dialogs
        allow = find_node(root, text="Allow")
        if allow is not None:
            tap(allow)
            time.sleep(1)
            root = ui_dump()
        ok = find_node(root, text="OK")
        if ok is not None:
            tap(ok)
            time.sleep(1)
            root = ui_dump()

        new_found_this_page = 0
        for node in root.iter("node"):
            text = node.attrib.get("text", "").strip()
            content_desc = node.attrib.get("content-desc", "").strip()
            clickable = node.attrib.get("clickable") == "true"

            label_text = text or content_desc
            if (
                label_text
                and label_text
                not in [
                    "OK",
                    "Cancel",
                    "Allow",
                    "Deny",
                    "CTS Verifier",
                    "System",
                    "Folded",
                    "More options",
                ]
                and not label_text.startswith("Verifier ")
            ):
                if label_text not in collected_labels:
                    collected_labels.add(label_text)
                    new_found_this_page += 1

                    # Determine if this node is a Category Header vs Test Item
                    if label_text.isupper() and len(label_text) < 35:
                        current_category = label_text
                        if current_category not in categories:
                            categories[current_category] = []
                    else:
                        # Test item under current category
                        target_cat = current_category
                        if (
                            "Device Admin" in label_text
                            or "Screen Lock" in label_text
                            or "Policy Serialization" in label_text
                        ):
                            target_cat = "DEVICE ADMINISTRATION"
                        elif (
                            "BYOD" in label_text
                            or "Managed" in label_text
                            or "Device Owner" in label_text
                            or "Provisioning" in label_text
                        ):
                            target_cat = "MANAGED PROVISIONING"
                        elif (
                            "Audio" in label_text
                            or "Sound" in label_text
                            or "Mic" in label_text
                            or "Speaker" in label_text
                        ):
                            target_cat = "AUDIO"
                        elif (
                            "Camera" in label_text
                            or "ITS" in label_text
                            or "FOV" in label_text
                            or "Bokeh" in label_text
                        ):
                            target_cat = "CAMERA"
                        elif "Bluetooth" in label_text or "BLE" in label_text:
                            target_cat = "BLUETOOTH"
                        elif (
                            "Sensor" in label_text
                            or "Accelerometer" in label_text
                            or "Barometer" in label_text
                            or "Biometric" in label_text
                        ):
                            target_cat = "SENSORS"
                        elif "Notification" in label_text or "CA Cert" in label_text:
                            target_cat = "NOTIFICATIONS & SYSTEM UI"

                        if target_cat not in categories:
                            categories[target_cat] = []
                        if label_text not in categories[target_cat]:
                            categories[target_cat].append(label_text)

        if new_found_this_page == 0:
            no_new_count += 1
            if no_new_count >= 3:
                print(
                    "No new test labels found after 3 consecutive swipes. Reached end of list."
                )
                break
        else:
            no_new_count = 0

        # Swipe down to expose more items
        adb("shell", "input", "swipe", "500", "1800", "500", "400", "300")
        time.sleep(1.5)

    # Clean up empty categories
    categories = {k: v for k, v in categories.items() if v}

    # Automatically scan existing pass_*.py scripts to annotate test items with automation status
    automated_scripts = {}
    if os.path.exists(VERIFIER_DIR):
        for fname in os.listdir(VERIFIER_DIR):
            if fname.startswith("pass_") and fname.endswith(".py"):
                fpath = os.path.join(VERIFIER_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as sf:
                        content = sf.read()
                        matches = re.findall(
                            r'navigate_to\s*\(\s*["\']([^"\']+)["\']', content
                        )
                        if matches:
                            for target_name in matches:
                                automated_scripts[target_name.strip().lower()] = fname
                        else:
                            title = (
                                fname[5:-3]
                                .replace("_test", "")
                                .replace("_", " ")
                                .lower()
                            )
                            automated_scripts[title] = fname
                except Exception as e:
                    print(
                        f"Warning: Failed to parse {fname} for automation status: {e}"
                    )

    annotated_categories = {}
    total_automated = 0
    total_untested = 0

    for cat_name, test_items in categories.items():
        annotated_categories[cat_name] = []
        for item in test_items:
            matched_script = None
            item_lower = item.lower()
            for target_label, script_file in automated_scripts.items():
                if (
                    target_label == item_lower
                    or target_label in item_lower
                    or item_lower in target_label
                ):
                    matched_script = script_file
                    break

            if matched_script:
                total_automated += 1
                annotated_categories[cat_name].append(
                    {"name": item, "automated": True, "script": matched_script}
                )
            else:
                total_untested += 1
                annotated_categories[cat_name].append(
                    {"name": item, "automated": False, "script": None}
                )

    total_test_items = total_automated + total_untested
    coverage_pct = (total_automated / max(1, total_test_items)) * 100

    result_data = {
        "total_categories": len(annotated_categories),
        "total_test_items": total_test_items,
        "total_automated_items": total_automated,
        "total_untested_items": total_untested,
        "automation_coverage": f"{coverage_pct:.1f}%",
        "categories": annotated_categories,
        "all_test_labels": sorted(list(collected_labels)),
    }

    os.makedirs(os.path.dirname(os.path.abspath(output_json_path)), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2)

    print(
        f"✓ Successfully collected {len(annotated_categories)} categories and {total_test_items} test items ({total_automated} automated, {total_untested} untested) into: {output_json_path}"
    )
    return output_json_path


def main():
    parser = argparse.ArgumentParser(
        description="CtsVerifier TestBuilder Automation Development Tool"
    )
    parser.add_argument(
        "--test",
        help="Test name as displayed in CtsVerifier list (e.g. 'Screen Lock Test')",
    )
    parser.add_argument("--output", help="Output Python script path")
    parser.add_argument(
        "--commands",
        help="Comma-separated sequence of commands to execute automatically (e.g. '1,swipe_up,pass')",
    )
    parser.add_argument(
        "--collect-test-module-names",
        "--collect-labels",
        action="store_true",
        help="Scroll through CtsVerifier and collect all test module labels into JSON file",
    )
    args = parser.parse_args()

    if args.collect_test_module_names:
        collect_test_module_names(args.output)
        sys.exit(0)

    if not args.test:
        parser.error(
            "--test is required unless --collect-test-module-names is specified."
        )

    builder = TestBuilder(args.test, args.output)
    if args.commands:
        cmd_list = [c.strip() for c in args.commands.split(",") if c.strip()]
        print(f"Executing pre-planned command sequence: {cmd_list}")
        # Inject commands into a loop
        def custom_interactive():
            setup()
            root, img, xml = builder.capture_snapshot("app_launched")
            print(f"Navigating to '{builder.test_name}'...")
            navigate_to(builder.test_name)
            time.sleep(2)
            root, img, xml = builder.capture_snapshot("test_opened")

            for cmd_raw in cmd_list:
                act_res = adb("shell", "dumpsys", "window", check=False)
                curr_act = "UnknownActivity"
                match = re.search(r"mCurrentFocus=Window\{[^\}]*\s+(\S+)\}", act_res)
                if match:
                    curr_act = match.group(1)

                elements = builder.get_interactive_elements(root)
                builder.print_menu(elements, curr_act)
                print(f"\nTestBuilder [AutoCommand]> {cmd_raw}")

                if cmd_raw.isdigit():
                    idx = int(cmd_raw) - 1
                    if 0 <= idx < len(elements):
                        el = elements[idx]
                        print(
                            f"Tapping element #{idx + 1}: {el['text'] or el['content_desc'] or el['resource_id']}..."
                        )
                        tap(el["node"])
                        if el["text"]:
                            builder.record_step(
                                f'root = ui_dump()\nnode = find_node(root, text="{el["text"]}")\nif node: tap(node)',
                                f'Tap {el["text"]}',
                            )
                        elif el["content_desc"]:
                            builder.record_step(
                                f'root = ui_dump()\nnode = find_node(root, content_desc="{el["content_desc"]}")\nif node: tap(node)',
                                f'Tap {el["content_desc"]}',
                            )
                        elif el["resource_id"]:
                            builder.record_step(
                                f'root = ui_dump()\nnode = find_node(root, resource_id="{el["resource_id"]}")\nif node: tap(node)',
                                f'Tap {el["resource_id"]}',
                            )
                        time.sleep(2)
                        root, img, xml = builder.capture_snapshot(
                            el["text"] or el["content_desc"] or "tapped"
                        )
                elif cmd_raw.startswith("tap "):
                    target = cmd_raw[4:].strip().strip("\"'")
                    node = find_node(root, text=target) or find_node(
                        root, content_desc=target
                    )
                    if node is not None:
                        print(f"Tapping '{target}'...")
                        tap(node)
                        builder.record_step(
                            f'root = ui_dump()\nnode = find_node(root, text="{target}") or find_node(root, content_desc="{target}")\nif node: tap(node)',
                            f"Tap {target}",
                        )
                        time.sleep(2)
                        root, img, xml = builder.capture_snapshot(target)
                elif cmd_raw == "swipe_up":
                    print("Swiping up...")
                    adb("shell", "input", "swipe", "720", "2500", "720", "500", "300")
                    builder.record_step(
                        'adb("shell", "input", "swipe", "720", "2500", "720", "500", "300")',
                        "Swipe up to unlock/scroll",
                    )
                    time.sleep(2)
                    root, img, xml = builder.capture_snapshot("swipe_up")
                elif cmd_raw.startswith("key "):
                    kcode = cmd_raw[4:].strip()
                    print(f"Sending keyevent {kcode}...")
                    adb("shell", "input", "keyevent", kcode)
                    builder.record_step(
                        f'adb("shell", "input", "keyevent", "{kcode}")',
                        f"Key event {kcode}",
                    )
                    time.sleep(2)
                    root, img, xml = builder.capture_snapshot(f"key_{kcode}")
                elif cmd_raw == "reboot":
                    print("Rebooting device...")
                    from cts_common import reboot_and_wait

                    reboot_and_wait()
                    builder.record_step(
                        "reboot_and_wait()", "Reboot and wait for boot complete"
                    )
                    root, img, xml = builder.capture_snapshot("post_reboot")
                elif cmd_raw.startswith("sleep "):
                    secs = float(cmd_raw[6:].strip())
                    print(f"Sleeping {secs}s...")
                    time.sleep(secs)
                    builder.record_step(f"time.sleep({secs})", f"Wait {secs}s")
                elif cmd_raw == "pass":
                    print("Tapping Pass button and completing test...")
                    pass_btn = find_node(root, content_desc="Pass") or find_node(
                        root, text="Pass"
                    )
                    if pass_btn is not None:
                        tap_pass(pass_btn)
                    builder.record_step(
                        """root = ui_dump()
pass_btn = find_node(root, content_desc="Pass") or find_node(root, text="Pass")
if pass_btn:
    tap_pass(pass_btn)
    time.sleep(2)""",
                        "Tap Pass button",
                    )
                    print("Navigating back to main activity for export...")
                    adb(
                        "shell",
                        "am",
                        "start",
                        "-n",
                        "com.android.cts.verifier/.CtsVerifierActivity",
                    )
                    builder.record_step(
                        'adb("shell", "am", "start", "-n", "com.android.cts.verifier/.CtsVerifierActivity")\ntime.sleep(3)\nexport_and_verify(TEST_NAME)',
                        "Export test result",
                    )
                    break

            builder.generate_script()

        custom_interactive()
    else:
        builder.run_interactive()


if __name__ == "__main__":
    main()
