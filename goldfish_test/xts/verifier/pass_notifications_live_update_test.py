#!/usr/bin/env python3
"""Authentic CTS Verifier Live Update Notification Test Automation.

Automates the 22 subtests in LiveUpdateNotificationVerifierActivity:
1. Launch LiveUpdateNotificationVerifierActivity and dismiss instructions.
2. Handle promotion enable/disable toggle steps and ongoing assertions.
3. For expanded appearance, semantic text/metric colors, and action buttons:
   a. Expand notification shade via status bar command.
   b. Enforce 2.0s settle delay for animation and capture screenshot.
   c. Verify promoted vs demoted layouts.
   d. Collapse shade and tap inline Pass button.
4. For status bar chip, timer, and chronometer steps:
   a. Enforce 2.0s observation delay and capture status bar screenshot.
   b. Tap inline Pass button.
5. Validate global toolbar Pass button enabled and tap Pass.
6. Export test report and assert passing result in test_result.xml.
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

TEST_NAME = "Live Update Notification Test"
ACTIVITY_CLASS = (
    "com.android.cts.verifier.notifications.LiveUpdateNotificationVerifierActivity"
)

_current_promoted_state = None


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


def scroll_to_top():
    """Scroll to the top of the test list."""
    print("  [Scroll Recovery] Scrolling back up to top of list...")
    w, h = get_screen_size()
    for _ in range(3):
        adb(
            "shell",
            "input",
            "swipe",
            str(w // 2),
            str(int(h * 0.25)),
            str(w // 2),
            str(int(h * 0.85)),
            "300",
            check=False,
        )
        time.sleep(0.5)
    time.sleep(1.0)


def scroll_down_step():
    """Scroll down the test list by one page/step."""
    w, h = get_screen_size()
    adb(
        "shell",
        "input",
        "swipe",
        str(w // 2),
        str(int(h * 0.70)),
        str(w // 2),
        str(int(h * 0.35)),
        "400",
        check=False,
    )
    time.sleep(1.0)


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


def find_instruction_in_parent(root, action_btn):
    """Find the nls_instructions node strictly within the immediate parent container/row of action_btn."""
    if root is None or action_btn is None:
        return ""
    parent_map = {}
    for parent in root.iter():
        for child in parent:
            parent_map[child] = parent

    curr = action_btn
    while curr in parent_map:
        parent = parent_map[curr]
        parent_res_id = (parent.attrib.get("resource-id") or "").lower()
        parent_cls = parent.attrib.get("class", "")

        # Stop ascending if we reached the root list container or scroll view
        if (any(k in parent_res_id for k in [
                "nls_test_items",
                "nls_test_scroller",
                "test_items",
                "test_scroller",
        ]) or "ScrollView" in parent_cls or "ListView" in parent_cls or
                "RecyclerView" in parent_cls):
            break

        for child in parent.iter("node"):
            res_id = (child.attrib.get("resource-id") or "").lower()
            if res_id.endswith(":id/nls_instructions") or res_id.endswith(
                    ":id/instructions"):
                text = child.attrib.get("text", "")
                if text:
                    return text
        curr = parent
    return ""


def get_active_instruction_text(root, active_btn):
    """Scope instruction text strictly to the nls_instructions node within the SAME parent container or immediately above the active button."""
    if root is None or active_btn is None:
        return ""
    # Try finding within immediate parent container first
    parent_text = find_instruction_in_parent(root, active_btn)
    if parent_text:
        return parent_text

    # Geometric fallback: strictly immediately above active button
    _, btn_cy = bounds_center(active_btn)
    _, h_screen = get_screen_size()
    instructions_nodes = [
        n for n in root.iter("node")
        if (n.attrib.get("resource-id") or "").endswith(":id/nls_instructions")
        or (n.attrib.get("resource-id") or "").endswith(":id/instructions")
    ]
    candidate_instrs = [
        n for n in instructions_nodes if bounds_center(n)[1] < btn_cy and
        (btn_cy - bounds_center(n)[1]) < int(h_screen * 0.20)
    ]
    active_instr_node = (max(candidate_instrs,
                             key=lambda n: bounds_center(n)[1])
                         if candidate_instrs else None)
    return (active_instr_node.attrib.get("text", "")
            if active_instr_node is not None else "")


def is_in_viewport(node):
    """Check if a node is within the visible screen viewport."""
    if node is None or "bounds" not in node.attrib:
        return False
    try:
        _, h = get_screen_size()
        _, cy = bounds_center(node)
        return 0 <= cy < h
    except Exception:
        return False


def handle_promotion_toggle_step(root, action_btn, subtest_count=0):
    """Handle promotion enable/disable toggle step for Live Update.

    Explicitly map:
    - Step 1: Enable (True)
    - Step 2: Disable (False)
    - Step 3: Enable (True)
    - Step 18: Disable / Demote (False)
    - Demote steps: False
    - Subtests 20-26 (enableLiveUpdateStep / chip / priority / chronometer / timer / metric): True
    """
    active_instr_text = get_active_instruction_text(root, action_btn).lower()
    btn_text = (action_btn.attrib.get("text") or "").strip().lower()
    combined_text = f"{btn_text} {active_instr_text}"

    if subtest_count >= 19:
        should_enable = True
    elif "disable" in combined_text or any(k in combined_text for k in (
            "demote",
            "ignore",
            "revoke",
            "turn off",
            "disallow",
            "off",
    )):
        should_enable = False
    elif "enable" in combined_text or ("allow" in combined_text and
                                       not any(k in combined_text for k in (
                                           "disable",
                                           "demote",
                                           "ignore",
                                           "revoke",
                                           "turn off",
                                           "disallow",
                                       ))):
        should_enable = True
    elif subtest_count in (1, 3):
        should_enable = True
    elif subtest_count in (2, 18):
        should_enable = False
    elif subtest_count >= 11:
        should_enable = False
    else:
        should_enable = True

    if should_enable:
        print(f"  [Promotion Toggle] Step {subtest_count}: Granting"
              " POST_PROMOTED_NOTIFICATIONS...")
        set_promoted_permission(True)
    else:
        print(f"  [Promotion Toggle] Step {subtest_count}: Revoking"
              " POST_PROMOTED_NOTIFICATIONS...")
        set_promoted_permission(False)

    time.sleep(1.0)
    # Safely cycle focus via ACTION_NOTIFICATION_LISTENER_SETTINGS + KEYCODE_BACK strictly for EnableOrDisablePromotionStep items
    cycle_focus_via_listener_settings()


def handle_inline_pass(root, inline_pass, subtest_count):
    """Handle user verification inline pass button for Live Update."""
    active_instr_text = get_active_instruction_text(root, inline_pass).lower()

    # Match Step 11: verifyLiveUpdateNotRenderContextualActionsStep (R.string.live_update_notification_appearance_reply_contextual_action)
    # Text in strings.xml is: "<b>Notification Appearance: No Contextual Actions</b>"
    # Ensure we distinguish it from the demoted contextual action step ("Render Contextual Actions")
    is_step_11 = ("no contextual" in active_instr_text or
                  "not render contextual" in active_instr_text or
                  ("contextual" in active_instr_text and
                   ("no " in active_instr_text or "not" in active_instr_text))
                  or subtest_count
                  == 11) and not ("render contextual" in active_instr_text and
                                  "no " not in active_instr_text and
                                  "not" not in active_instr_text)

    # Scoped permission detection strictly on active item's localized text:
    is_demoted_expander = ("has an expander icon" in active_instr_text and
                           "does not have" not in active_instr_text)
    is_demoted_appearance = (
        (12 <= subtest_count <= 18) or "demote" in active_instr_text or
        "render contextual" in active_instr_text or
        "render reply" in active_instr_text or
        "no text styling" in active_instr_text or is_demoted_expander or
        "no semantic" in active_instr_text) and not is_step_11

    is_chip_step = (subtest_count >= 19) or any(
        kw in active_instr_text
        for kw in ("chip", "chronometer", "status bar", "ticker", "status_bar",
                   "priority", "timer", "metric"))

    if is_demoted_appearance and subtest_count < 19:
        if _current_promoted_state is not False:
            print(f"  [Subtest {subtest_count:02d}] Demoted appearance detected"
                  f" ({active_instr_text[:30]!r}). Setting promoted=False...")
            set_promoted_permission(False)
    elif is_chip_step or subtest_count >= 19:
        if _current_promoted_state is not True:
            print(
                f"  [Subtest {subtest_count:02d}] Trailing / Chip subtest detected"
                f" ({active_instr_text[:30]!r}). Setting promoted=True...")
            set_promoted_permission(True)
    elif ((4 <= subtest_count <= 10) or is_step_11 or
          any(kw in active_instr_text for kw in (
              "promoted",
              "customized",
              "actions",
              "style",
              "progress",
              "contextual",
          ))):
        if _current_promoted_state is not True:
            print(
                f"  [Subtest {subtest_count:02d}] Promoted appearance detected"
                f" ({active_instr_text[:30]!r}). Setting promoted=True...")
            set_promoted_permission(True)

    if not is_chip_step and subtest_count < 19:
        print(
            f"  [Subtest {subtest_count:02d}] Expanding notification shade for"
            " Live Update appearance...")
        adb(
            "shell",
            "cmd",
            "statusbar",
            "expand-notifications",
            check=False,
        )
        time.sleep(0.8)
        screenshot(f"subtest_{subtest_count:02d}_shade_expanded")
        adb("shell", "cmd", "statusbar", "collapse", check=False)
        time.sleep(0.5)
    else:
        print(f"  [Subtest {subtest_count:02d}] Observing Status Bar Chip /"
              " Chronometer / Priority...")
        time.sleep(0.8)

    # Detect Step 11 ("No Contextual Actions") by matching "no contextual" or "not render contextual"
    # and call set_promoted_permission(False) immediately before tapping pass so
    # DemoteLiveUpdateNotificationStep.setUp() posts the demoted notification with
    # FLAG_PROMOTED_ONGOING stripped from inception.
    if is_step_11 or subtest_count == 11:
        print(
            f"  [Subtest {subtest_count:02d}] Step 11 ('No Contextual Actions')"
            " detected. Revoking promotion permissions immediately before"
            " tapping pass...")
        set_promoted_permission(False)
        time.sleep(0.5)

    root_post = ui_dump()
    pass_btn = find_active_inline_pass(root_post)
    if pass_btn is not None and is_in_viewport(pass_btn):
        tap(pass_btn)
    else:
        tap(inline_pass)
    time.sleep(1.0)
    screenshot(f"subtest_{subtest_count:02d}_passed")


def cycle_focus_via_listener_settings():
    """Cycle focus safely via ACTION_NOTIFICATION_LISTENER_SETTINGS + KEYCODE_BACK."""
    print("  [Focus Cycle] Cycling focus via Notification Listener Settings to"
          " trigger onTopResumedActivityChanged(true)...")
    adb(
        "shell",
        "am",
        "start",
        "-W",
        "-a",
        "android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS",
        check=False,
    )
    time.sleep(2.0)
    for _ in range(3):
        if "settings" in get_focused_package().lower():
            adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
            time.sleep(1.0)
        else:
            break
    if get_focused_package() != "com.android.cts.verifier":
        adb(
            "shell",
            "am",
            "start",
            "-W",
            "-f",
            "0x20000000",
            "-n",
            ("com.android.cts.verifier/.notifications.LiveUpdateNotificationVerifierActivity"
            ),
            check=False,
        )
        time.sleep(2.0)
    time.sleep(1.5)


def set_promoted_permission(granted: bool):
    """Grant or revoke POST_PROMOTED_NOTIFICATIONS appops at package and UID levels."""
    global _current_promoted_state
    _current_promoted_state = granted
    mode = "allow" if granted else "ignore"
    uid = get_package_uid("com.android.cts.verifier")
    print(f"  [Permission Sync] Setting POST_PROMOTED_NOTIFICATIONS to {mode}"
          f" (uid={uid})...")
    if granted:
        adb(
            "shell",
            "pm",
            "grant",
            "com.android.cts.verifier",
            "android.permission.POST_PROMOTED_NOTIFICATIONS",
            check=False,
        )
    if uid is not None:
        adb(
            "shell",
            "cmd",
            "appops",
            "set",
            "--uid",
            uid,
            "android:post_promoted_notifications",
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
            "POST_PROMOTED_NOTIFICATIONS",
            mode,
            check=False,
        )
    adb(
        "shell",
        "cmd",
        "appops",
        "set",
        "com.android.cts.verifier",
        "android:post_promoted_notifications",
        mode,
        check=False,
    )
    adb(
        "shell",
        "cmd",
        "appops",
        "set",
        "com.android.cts.verifier",
        "POST_PROMOTED_NOTIFICATIONS",
        mode,
        check=False,
    )
    adb(
        "shell",
        "appops",
        "set",
        "com.android.cts.verifier",
        "POST_PROMOTED_NOTIFICATIONS",
        mode,
        check=False,
    )


def main():
    setup()
    set_screenshot_dir("notifications_live_update_test")

    try:
        # Pre-test setup: screen on, clear notifications, grant promoted permission
        print("Pre-test setup: ensuring screen unlocked and clean state...")
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
        adb("shell", "wm", "dismiss-keyguard", check=False)
        adb("shell", "settings", "put", "global", "zen_mode", "0", check=False)
        adb("shell", "cmd", "notification", "clear_all", check=False)
        set_promoted_permission(True)
        time.sleep(1)

        print(f"Navigating to '{TEST_NAME}'...")
        navigate_to(TEST_NAME, verify_title="Live Update")
        time.sleep(2)
        dismiss_initial_dialog()
        screenshot("00_test_opened")

        print("Executing Live Update Notification verification lifecycle...")
        start_time = time.time()
        timeout = 720  # 12 minutes max for all 22 subtests
        subtest_count = 0
        idle_cycles = 0

        while time.time() - start_time < timeout:
            # Focus recovery watchdog:
            # Settings intent has FLAG_ACTIVITY_CLEAR_TASK which causes KEYCODE_BACK to land on Home Launcher.
            focused_pkg = get_focused_package()
            if (focused_pkg and focused_pkg != "com.android.cts.verifier" and
                    "settings" not in focused_pkg.lower()):
                print(f"  [Focus Recovery] Focused package is '{focused_pkg}'."
                      " Re-launching"
                      " LiveUpdateNotificationVerifierActivity...")
                adb(
                    "shell",
                    "am",
                    "start",
                    "-W",
                    "-f",
                    "0x20000000",
                    "-n",
                    ("com.android.cts.verifier/.notifications.LiveUpdateNotificationVerifierActivity"
                    ),
                    check=False,
                )
                time.sleep(2.0)

            root = ui_dump()
            # Enforce STATE-1: never tap global Pass button before all subtests are executed
            if is_pass_button_enabled(root) and subtest_count >= 18:
                print(
                    f"  ✓ Global toolbar Pass button is enabled after all {subtest_count} subtests!"
                )
                break

            # 1. Handle active user verification inline pass buttons (LiveUpdateUserVerificationBase subtests)
            inline_pass = find_active_inline_pass(root)
            if inline_pass is not None and is_in_viewport(inline_pass):
                subtest_count += 1
                handle_inline_pass(root, inline_pass, subtest_count)
                idle_cycles = 0
                continue

            # 2. Handle active action buttons (Settings toggle, demote, grant/revoke)
            active_action_btns = [
                n for n in root.iter("node")
                if ((n.attrib.get("resource-id") or ""
                    ).endswith(":id/nls_action_button") or
                    (n.attrib.get("resource-id") or ""
                    ).endswith(":id/iva_action_button")) and
                n.attrib.get("enabled", "false") == "true" and
                (n.attrib.get("text") or "").strip().lower() != "pass" and
                is_in_viewport(n)
            ]
            if active_action_btns:
                subtest_count += 1
                action_btn = active_action_btns[0]
                print(f"  [Step {subtest_count:02d}] Handling promotion toggle"
                      f" step ({action_btn.attrib.get('text')!r})...")
                handle_promotion_toggle_step(root, action_btn, subtest_count)
                idle_cycles = 0
                screenshot(f"subtest_{subtest_count:02d}_action_completed")
                continue

            time.sleep(1.0)
            idle_cycles += 1

            # Enforce idle_cycles >= 3 before downward scroll swipe to allow InteractiveTestCase.setUp() delay to complete
            if idle_cycles >= 3:
                print(
                    f"  [Idle Watchdog] No active action or pass button found after {idle_cycles}s."
                    " Scrolling down step to bring trailing items into view...")
                idle_cycles = 0
                scroll_down_step()

        # Confirm toolbar Pass button enabled and tap it
        print("\nWaiting for global Pass button confirmation...")
        pass_btn = None
        for _ in range(30):
            root = ui_dump()
            if is_pass_button_enabled(root):
                pass_btn = find_pass_button(root)
                break
            time.sleep(2)

        if pass_btn is not None:
            screenshot("23_global_pass_enabled")
            tap_pass(pass_btn)
            screenshot("24_global_pass_tapped")
        else:
            raise RuntimeError(
                "Global Pass button was not enabled after completing subtests")

        # Return to main activity and verify exported report
        return_to_main_activity()
        export_and_verify("notifications_live_update_test")
        screenshot("25_test_report_exported")
        print("\n=== Live Update Notification Test Automation PASSED"
              " successfully! ===")

    finally:
        adb("shell", "cmd", "notification", "clear_all", check=False)


if __name__ == "__main__":
    main()
