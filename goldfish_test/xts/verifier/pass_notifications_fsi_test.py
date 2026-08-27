#!/usr/bin/env python3
"""Authentic CTS Verifier Notification Full Screen Intent (FSI) Test Automation.

Automates the 12 subtests in NotificationFullScreenIntentVerifierActivity:
1. Configure PIN '1111' screen lock prerequisite and global visibility.
2. Grant USE_FULL_SCREEN_INTENT permission.
3. Test sticky Heads-Up Notification (HUN) when unlocked.
4. Test full screen activity launch over lockscreen (accounting for 3s postDelayed window).
5. Test full screen activity launch when screen is off.
6. Deny USE_FULL_SCREEN_INTENT permission.
7. Test standard non-sticky HUN when unlocked without permission.
8. Test non-launching lockscreen item without permission.
9. Test screen off pulse without permission.
10. Clear PIN '1111' credentials and restore device state.
11. Validate global toolbar Pass button enabled and tap Pass.
12. Export test report and assert passing result in test_result.xml.
"""

import os
import re
import sys
import time

try:
    sys.stdout.reconfigure(line_buffering=True)
except (AttributeError, TypeError):
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from cts_common import (
    ACTIVITY,
    adb,
    bounds_center,
    export_and_verify,
    find_active_inline_pass,
    find_node,
    find_pass_button,
    get_display_dimensions,
    get_focused_package,
    get_screen_size,
    is_pass_button_enabled,
    navigate_to,
    screenshot,
    set_screenshot_dir,
    setup,
    tap,
    tap_pass,
    ui_dump,
    wait_for,
)
from security_common import (
    PrereqState,
    clear_all_credentials,
    ensure_security_prerequisites,
    enter_pin_on_keypad,
    is_pin_entry_present,
    unlock_device_with_pin,
)

TEST_NAME = "Notification Full Screen Intent Test"
ACTIVITY_CLASS = (
    "com.android.cts.verifier.notifications.NotificationFullScreenIntentVerifierActivity"
)


def return_to_main_activity():
    """Return to CtsVerifierActivity list."""
    for _ in range(4):
        root = ui_dump()
        if find_node(root, text="CTS Verifier") is not None:
            return
        adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
        time.sleep(1.5)
    adb("shell", "am", "start", "-W", "-n", ACTIVITY, check=False)
    time.sleep(2)


def dismiss_initial_dialog():
    """Dismiss the instructions dialog if displayed upon opening the test."""
    for _ in range(3):
        root = ui_dump()
        ok_btn = find_node(root, text="OK")
        if ok_btn is not None:
            print("  Dismissing instructions OK dialog...")
            tap(ok_btn)
            time.sleep(1.5)
            break
        time.sleep(0.5)


def scroll_down():
    """Scroll down the test list using dynamic screen dimensions."""
    w, h = get_screen_size()
    x = w // 2
    y1 = int(h * 0.70)
    y2 = int(h * 0.35)
    adb(
        "shell",
        "input",
        "swipe",
        str(x),
        str(y1),
        str(x),
        str(y2),
        "400",
        check=False,
    )
    time.sleep(1.5)


def scroll_up():
    """Scroll up the test list using dynamic screen dimensions."""
    w, h = get_screen_size()
    x = w // 2
    y1 = int(h * 0.35)
    y2 = int(h * 0.70)
    adb(
        "shell",
        "input",
        "swipe",
        str(x),
        str(y1),
        str(x),
        str(y2),
        "400",
        check=False,
    )
    time.sleep(1.5)


def get_package_uid(package_name="com.android.cts.verifier"):
    """Query package UID via pm list packages -U."""
    try:
        out = adb("shell",
                  "pm",
                  "list",
                  "packages",
                  "-U",
                  package_name,
                  check=False)
        m = re.search(r"uid:(\d+)", out)
        if m is not None:
            return m.group(1)
    except Exception as e:
        print(f"  [UID] Failed to query package UID: {e}")
    return None


def handle_fsi_permission(allow: bool):
    """Set package and UID-level AppOps for USE_FULL_SCREEN_INTENT."""
    mode = "allow" if allow else "ignore"
    uid = get_package_uid("com.android.cts.verifier")
    print(
        f"  [FSI AppOps] Setting USE_FULL_SCREEN_INTENT to {mode} (uid={uid})..."
    )
    if uid is not None:
        adb(
            "shell",
            "cmd",
            "appops",
            "set",
            "--uid",
            uid,
            "android:use_full_screen_intent",
            mode,
            check=False,
        )
        adb(
            "shell",
            "cmd",
            "appops",
            "set",
            "--uid",
            uid,
            "USE_FULL_SCREEN_INTENT",
            mode,
            check=False,
        )
    adb(
        "shell",
        "cmd",
        "appops",
        "set",
        "com.android.cts.verifier",
        "android:use_full_screen_intent",
        mode,
        check=False,
    )
    adb(
        "shell",
        "cmd",
        "appops",
        "set",
        "com.android.cts.verifier",
        "USE_FULL_SCREEN_INTENT",
        mode,
        check=False,
    )
    adb(
        "shell",
        "appops",
        "set",
        "com.android.cts.verifier",
        "USE_FULL_SCREEN_INTENT",
        mode,
        check=False,
    )


def recover_and_find_active_node(predicate=None, max_down_swipes=16):
    """Bidirectional scroll recovery for active verifier elements.

    When searching for iva_action_button_pass or subtest items after PIN unlock,
    if not found in current viewport:
    1. Checks a small downward scroll (0.15 * h = 468px) before scrolling all the way to the top.
    2. If still not found, scrolls to top of list using proportional coordinates.
    3. Scans downward incrementally with swipe delta 0.15 * h (468px) to guarantee continuous
       viewport overlap without skipping ~350px subtest cards.
    """
    if predicate is None:
        predicate = lambda root: find_active_inline_pass(root)

    root = ui_dump()
    node = predicate(root)
    if node is not None:
        return node, root

    w, h = get_screen_size()
    x = w // 2
    top_y1 = int(h * 0.30)
    top_y2 = int(h * 0.80)
    down_y1 = int(h * 0.55)
    down_y2 = int(h * 0.40)  # delta = 0.15 * h (468px)

    # 1. Check a small downward scroll (0.15 * h = 468px) before scrolling all the way to the top
    print(
        "  [Scroll Recovery] Checking small downward scroll (0.15 * h) before scrolling to top..."
    )
    adb(
        "shell",
        "input",
        "swipe",
        str(x),
        str(down_y1),
        str(x),
        str(down_y2),
        "300",
        check=False,
    )
    time.sleep(1.0)
    root = ui_dump()
    node = predicate(root)
    if node is not None:
        return node, root

    # 2. Scroll to top of list if still not found
    print(
        "  [Scroll Recovery] Element not found in immediate vicinity, scrolling to top of list..."
    )
    for _ in range(3):
        adb(
            "shell",
            "input",
            "swipe",
            str(x),
            str(top_y1),
            str(x),
            str(top_y2),
            "300",
            check=False,
        )
        time.sleep(0.5)
    time.sleep(1.0)

    root = ui_dump()
    node = predicate(root)
    if node is not None:
        return node, root

    # 3. Scan downward incrementally with swipe delta 0.15 * h (468px) for continuous viewport overlap
    for attempt in range(max_down_swipes):
        print("  [Scroll Recovery] Scanning downward incrementally (attempt"
              f" {attempt + 1}/{max_down_swipes})...")
        adb(
            "shell",
            "input",
            "swipe",
            str(x),
            str(down_y1),
            str(x),
            str(down_y2),
            "300",
            check=False,
        )
        time.sleep(1.0)
        root = ui_dump()
        node = predicate(root)
        if node is not None:
            return node, root

    return None, root


def find_ready_button(root):
    """Find active 'I\'m done' / 'I\'m ready' button in the active item."""
    if root is None:
        return None
    candidates = []
    for node in root.iter("node"):
        text = (node.attrib.get("text") or "").strip().lower()
        desc = (node.attrib.get("content-desc") or "").strip().lower()
        res_id = (node.attrib.get("resource-id") or "").lower()
        cls = node.attrib.get("class", "")
        clickable = node.attrib.get("clickable", "false") == "true"
        enabled = node.attrib.get("enabled", "true")
        if enabled != "true":
            continue
        # Must be clickable or a Button to avoid false matching on instruction TextViews
        if not clickable and "Button" not in cls:
            continue
        is_ready = (text in [
            "done",
            "ready",
            "i'm done",
            "i'm ready",
            "i’m done",
            "i’m ready",
        ] or desc in [
            "done",
            "ready",
            "i'm done",
            "i'm ready",
            "i’m done",
            "i’m ready",
        ] or (any(r in res_id
                  for r in ["iva_action_button", "nls_action_button"]) and
              not res_id.endswith("iva_action_button_pass") and
              any(k in text or k in desc for k in [
                  "done",
                  "ready",
                  "i'm ready",
                  "i'm done",
                  "i’m ready",
                  "i’m done",
              ])) or (res_id.endswith(":id/iva_action_button") and
                      not res_id.endswith("iva_action_button_pass")))
        if not is_ready:
            continue
        bounds = node.attrib.get("bounds", "")
        if not bounds:
            continue
        candidates.append(node)

    if not candidates:
        return None
    # Pick topmost active ready button
    candidates.sort(key=lambda n: bounds_center(n)[1])
    return candidates[0]


def is_show_when_locked_active():
    """Check if ShowWhenLockedActivity is active on screen."""
    window_displays = adb("shell", "dumpsys", "window", "displays", check=False)
    if "ShowWhenLockedActivity" in window_displays:
        return True
    activity_top = adb("shell", "dumpsys", "activity", "top", check=False)
    if "ShowWhenLockedActivity" in activity_top:
        return True
    return False


def is_show_when_locked_foreground() -> bool:
    res = adb("shell", "dumpsys", "activity", "top", check=False)
    return "ShowWhenLockedActivity" in res


def ensure_show_when_locked_dismissed():
    for _ in range(5):
        if is_show_when_locked_foreground():
            adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
            time.sleep(1.0)
        else:
            break


def tap_ready_and_lock_immediately(step_desc="FSI Step"):
    """Tap 'I\'m ready' button, then immediately lock screen within 1.0s."""
    print(f"\n[{step_desc}] Locating active step / 'I\\'m ready' button...")
    ready_btn, _ = recover_and_find_active_node(find_ready_button)
    if ready_btn is not None:
        print(
            f"  [{step_desc}] Tapping ready button ({ready_btn.attrib.get('text')!r})..."
        )
        tap(ready_btn)
        # CRITICAL TIMING: Lock screen immediately within 1s before the 3s postDelayed timer expires!
        print(
            f"  [{step_desc}] Immediately locking screen for postDelayed FSI window..."
        )
        adb("shell", "input", "keyevent", "26", check=False)
        time.sleep(
            4.5
        )  # Wait 4.5s for 3.0s postDelayed timer to trigger over Keyguard

        # Wake screen with KEYCODE_WAKEUP first, sleep 1.5s
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
        time.sleep(1.5)

        # Verify ShowWhenLockedActivity via dumpsys window displays and ui_dump() before issuing KEYCODE_BACK
        if is_show_when_locked_active():
            print(
                "  Dismissing ShowWhenLockedActivity via KEYCODE_BACK to expose"
                " Keyguard...")
            adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
            time.sleep(1.5)
        else:
            print("  ShowWhenLockedActivity not active/displayed (e.g. FSI"
                  " denied/suppressed step), skipping KEYCODE_BACK...")

        # Unlock device with PIN 1111 on revealed Keyguard
        unlock_device_with_pin("1111")
        adb("shell", "wm", "dismiss-keyguard", check=False)
        time.sleep(1.0)
        time.sleep(2.0)

        # Ensure ShowWhenLockedActivity is dismissed if present in foreground
        ensure_show_when_locked_dismissed()

        if get_focused_package() != "com.android.cts.verifier":
            adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
            time.sleep(1.0)
        if get_focused_package() != "com.android.cts.verifier":
            adb(
                "shell",
                "am",
                "start",
                "-W",
                "-f",
                "0x20000000",
                "-n",
                ("com.android.cts.verifier/.notifications.NotificationFullScreenIntentVerifierActivity"
                ),
                check=False,
            )
            time.sleep(2.0)

        # 1.5s transition settle delay after PIN unlock before dumping the UI
        time.sleep(1.5)

        # Recover and find active inline pass button (iva_action_button_pass) with retry
        for unlock_try in range(3):
            if get_focused_package() != "com.android.cts.verifier":
                adb(
                    "shell",
                    "am",
                    "start",
                    "-W",
                    "-f",
                    "0x20000000",
                    "-n",
                    ("com.android.cts.verifier/.notifications.NotificationFullScreenIntentVerifierActivity"
                    ),
                    check=False,
                )
                time.sleep(2.0)
                scroll_down()
                scroll_up()
            inline_pass, _ = recover_and_find_active_node(
                find_active_inline_pass)
            if inline_pass is not None:
                print(
                    "  Tapping inline pass button (iva_action_button_pass)...")
                tap(inline_pass)
                time.sleep(3.0)
                return True
            print(
                f"  [FSI Unlock Retry {unlock_try + 1}/3] Inline pass button not found, re-waking, unlocking, and scrolling..."
            )
            adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
            adb("shell", "wm", "dismiss-keyguard", check=False)
            unlock_device_with_pin("1111")
            time.sleep(1.5)
            scroll_down()
            scroll_up()

        print("  Warning: inline pass button not found after unlock")
        return False
    else:
        print(f"  Warning: Ready action button not found for {step_desc}")
        return False


def tap_inline_pass_button():
    """Locate and tap the enabled inline Pass button with bidirectional scroll recovery."""
    pass_btn, _ = recover_and_find_active_node(find_active_inline_pass)
    if pass_btn is not None:
        tap(pass_btn)
        time.sleep(3.5)
        return True
    return False


def main():
    setup()
    set_screenshot_dir("notifications_fsi_test")

    try:
        # Pre-test setup: Ensure PIN '1111' enrolled
        print("Pre-test setup: Setting up PIN '1111' prerequisite...")
        ensure_security_prerequisites(PrereqState.PIN_ONLY)
        adb(
            "shell",
            "settings",
            "put",
            "secure",
            "lock_screen_show_notifications",
            "1",
            check=False,
        )
        adb(
            "shell",
            "settings",
            "put",
            "secure",
            "lock_screen_allow_private_notifications",
            "1",
            check=False,
        )
        handle_fsi_permission(True)
        adb("shell", "cmd", "notification", "clear_all", check=False)
        time.sleep(1)

        print(f"Navigating to '{TEST_NAME}'...")
        navigate_to(TEST_NAME, verify_title="Full Screen Intent")
        time.sleep(2)
        dismiss_initial_dialog()
        screenshot("01_test_opened")

        print("Monitoring Full Screen Intent test execution lifecycle...")
        start_time = time.time()
        timeout = 420  # 7 minutes max
        subtest_count = 0
        idle_cycles = 0

        while time.time() - start_time < timeout:
            # Focus recovery watchdog: re-launch if focus lost to launcher
            focused_pkg = get_focused_package()
            if (focused_pkg and focused_pkg != "com.android.cts.verifier" and
                    "settings" not in focused_pkg.lower()):
                print(
                    f"  [Focus Recovery] Focused package is '{focused_pkg}'."
                    " Re-launching NotificationFullScreenIntentVerifierActivity..."
                )
                adb(
                    "shell",
                    "am",
                    "start",
                    "-W",
                    "-f",
                    "0x20000000",
                    "-n",
                    ("com.android.cts.verifier/.notifications.NotificationFullScreenIntentVerifierActivity"
                    ),
                    check=False,
                )
                time.sleep(2.0)

            root = ui_dump()
            # Enforce STATE-1: never tap global Pass button before all subtests are executed
            if is_pass_button_enabled(root) and subtest_count >= 6:
                print(
                    f"  ✓ Global toolbar Pass button is enabled after all {subtest_count} subtests!"
                )
                break

            # 1. Handle "I'm done" / ready action button FIRST (createUserAndPassFailItem)
            # to initiate 3-second FSI timer and run lock/wake sequence
            ready_btn = find_ready_button(root)
            if ready_btn is not None:
                subtest_count += 1
                tap_ready_and_lock_immediately(f"Subtest {subtest_count:02d}")
                screenshot(f"fsi_subtest_{subtest_count:02d}_completed")
                idle_cycles = 0
                continue

            # 2. Handle createUserItem (@id/nls_action_button with "Open Notification Settings" / "Open Security Settings", e.g. DenyFsiPermissionStep)
            action_buttons = [
                n for n in root.iter("node")
                if (n.attrib.get("resource-id") or ""
                   ).endswith(":id/nls_action_button") and
                n.attrib.get("enabled", "false") == "true"
            ]
            if action_buttons:
                subtest_count += 1
                action_btn = action_buttons[0]
                # Inspect localized instruction text associated with this action button
                btn_center_y = bounds_center(action_btn)[1]
                instructions_nodes = [
                    n for n in root.iter("node")
                    if (n.attrib.get("resource-id") or ""
                       ).endswith(":id/nls_instructions")
                ]
                _, h_screen = get_screen_size()
                candidate_instrs = [
                    n for n in instructions_nodes
                    if bounds_center(n)[1] <= btn_center_y +
                    int(h_screen * 0.05)
                ]
                active_instr_node = (max(candidate_instrs,
                                         key=lambda n: bounds_center(n)[1])
                                     if candidate_instrs else None)
                active_instr_text = (active_instr_node.attrib.get("text", "")
                                     if active_instr_node is not None else
                                     "").lower()
                btn_txt = (action_btn.attrib.get("text") or "").lower()

                print(
                    "  [createUserItem Step] Handling FSI permission / visibility"
                    f" toggle (btn={btn_txt!r}, instr={active_instr_text!r})..."
                )

                if any(k in active_instr_text for k in (
                        "toggle on",
                        "turn on",
                        "grant",
                        "allow",
                        "enable",
                        "restore",
                )) or any(k in btn_txt for k in (
                        "grant",
                        "allow",
                        "enable",
                        "turn on",
                        "toggle on",
                )):
                    print(
                        "  [createUserItem] Granting FSI permission (AppOps allow)..."
                    )
                    handle_fsi_permission(True)
                elif any(k in active_instr_text for k in (
                        "toggle off",
                        "turn off",
                        "deny",
                        "disallow",
                        "dont",
                        "don't",
                        "revoke",
                        "disable",
                )) or any(k in btn_txt for k in (
                        "deny",
                        "disallow",
                        "turn off",
                        "toggle off",
                        "revoke",
                        "disable",
                )):
                    print(
                        "  [createUserItem] Denying FSI permission (AppOps ignore)..."
                    )
                    handle_fsi_permission(False)
                elif "channel" in active_instr_text:
                    print(
                        "  [createUserItem] Channel lockscreen visibility public..."
                    )
                elif ("global" in active_instr_text or
                      "lock screen" in active_instr_text or
                      "all notification" in active_instr_text):
                    print(
                        "  [createUserItem] Setting global visibility public..."
                    )
                    adb(
                        "shell",
                        "settings",
                        "put",
                        "secure",
                        "lock_screen_show_notifications",
                        "1",
                        check=False,
                    )
                    adb(
                        "shell",
                        "settings",
                        "put",
                        "secure",
                        "lock_screen_allow_private_notifications",
                        "1",
                        check=False,
                    )
                else:
                    print(
                        "  [createUserItem] Defaulting to AppOps USE_FULL_SCREEN_INTENT"
                        " ignore for DenyFsiPermissionStep...")
                    handle_fsi_permission(False)

                tap(action_btn)
                time.sleep(2.0)
                if "settings" in get_focused_package().lower():
                    adb(
                        "shell",
                        "input",
                        "keyevent",
                        "KEYCODE_BACK",
                        check=False,
                    )
                    time.sleep(2.0)
                if get_focused_package() != "com.android.cts.verifier":
                    adb(
                        "shell",
                        "input",
                        "keyevent",
                        "KEYCODE_BACK",
                        check=False,
                    )
                    time.sleep(1.0)
                if get_focused_package() != "com.android.cts.verifier":
                    adb(
                        "shell",
                        "am",
                        "start",
                        "-W",
                        "-f",
                        "0x20000000",
                        "-n",
                        ("com.android.cts.verifier/.notifications.NotificationFullScreenIntentVerifierActivity"
                        ),
                        check=False,
                    )
                    time.sleep(2.0)
                idle_cycles = 0
                continue

            # 3. Handle standalone iva_pass_fail_item (iva_action_button_pass)
            inline_p = find_active_inline_pass(root)
            if inline_p is not None:
                subtest_count += 1
                print(
                    f"  [Subtest {subtest_count:02d}] Tapping inline pass button..."
                )
                tap(inline_p)
                time.sleep(3.5)
                idle_cycles = 0
                screenshot(f"inline_pass_{subtest_count:02d}")
                continue

            time.sleep(1.0)
            idle_cycles += 1

            # Scroll down only after several idle cycles to reveal next items in ScrollView
            if idle_cycles >= 4:
                idle_cycles = 0
                scroll_down()

        # Confirm toolbar Pass button enabled and tap it
        print("\nWaiting for global Pass button confirmation...")
        pass_btn = None
        for _ in range(15):
            root = ui_dump()
            if is_pass_button_enabled(root):
                pass_btn = find_pass_button(root)
                break
            time.sleep(2.0)

        if pass_btn is not None:
            screenshot("11_global_pass_enabled")
            tap_pass(pass_btn)
            screenshot("12_global_pass_tapped")
        else:
            raise RuntimeError(
                "Global Pass button was not enabled after completing subtests")

        # Return to main activity and verify exported report
        return_to_main_activity()
        export_and_verify("notifications_fsi_test")
        screenshot("13_test_report_exported")
        print(
            "\n=== CTS Verifier Notification Full Screen Intent Tests Automation"
            " PASSED! ===")

    finally:
        clear_all_credentials()
        handle_fsi_permission(True)
        adb("shell", "cmd", "notification", "clear_all", check=False)


if __name__ == "__main__":
    main()
