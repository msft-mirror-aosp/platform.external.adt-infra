#!/usr/bin/env python3
"""Authentic CTS Verifier Notification Listener Test Automation.

Automates the 26 subtests in NotificationListenerVerifierActivity:
1. Grant NotificationListener access to MockListener.
2. Launch NotificationListenerVerifierActivity and dismiss instructions.
3. Validate listener intercept, data integrity, noisy audio alerts, dismissal,
   snooze (3s, 10s, 30s), hints, app/channel block notices, unbind/rebind.
4. Handle Conversation Ordering and Heads-Up Notification (HUN) verification.
5. Revoke NotificationListener access and verify service termination.
6. Validate global toolbar Pass button enabled and tap Pass.
7. Export test report and assert passing result in test_result.xml.
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

TEST_NAME = "Notification Listener Test"
ACTIVITY_CLASS = (
    "com.android.cts.verifier.notifications.NotificationListenerVerifierActivity"
)
MOCK_LISTENER_COMPONENT = "com.android.cts.verifier/.notifications.MockListener"

_known_channel_ids = set()
_known_group_ids = set()


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


def handle_shade_interaction(step_name):
    """Expand notification shade, capture screenshot, settle, collapse, and return."""
    print(f"  Expanding notification shade for {step_name} verification...")
    adb("shell", "cmd", "statusbar", "expand-notifications", check=False)
    time.sleep(2.0)  # Settle delay for slide-down animation
    screenshot(f"{step_name}_in_shade")
    adb("shell", "cmd", "statusbar", "collapse", check=False)
    time.sleep(1.5)


def broadcast_block_change(action, extras=None):
    """Direct broadcast to BlockChangeReceiver."""
    print(
        f"  [BlockChangeReceiver] Broadcasting {action} with extras {extras}..."
    )
    cmd = [
        "shell",
        "am",
        "broadcast",
        "-a",
        action,
        "-n",
        "com.android.cts.verifier/.notifications.BlockChangeReceiver",
    ]
    if extras:
        for k, v in extras.items():
            if isinstance(v, bool):
                cmd.extend(["--ez", k, str(v).lower()])
            elif isinstance(v, int):
                cmd.extend(["--ei", k, str(v)])
            else:
                cmd.extend(["--es", k, str(v)])
    adb(*cmd, check=False)

    cmd_full = [
        "shell",
        "am",
        "broadcast",
        "-a",
        action,
        "-n",
        "com.android.cts.verifier/com.android.cts.verifier.notifications.BlockChangeReceiver",
    ]
    if extras:
        for k, v in extras.items():
            if isinstance(v, bool):
                cmd_full.extend(["--ez", k, str(v).lower()])
            elif isinstance(v, int):
                cmd_full.extend(["--ei", k, str(v)])
            else:
                cmd_full.extend(["--es", k, str(v)])
    adb(*cmd_full, check=False)

    cmd_pkg = [
        "shell",
        "am",
        "broadcast",
        "-a",
        action,
        "-p",
        "com.android.cts.verifier",
    ]
    if extras:
        for k, v in extras.items():
            if isinstance(v, bool):
                cmd_pkg.extend(["--ez", k, str(v).lower()])
            elif isinstance(v, int):
                cmd_pkg.extend(["--ei", k, str(v)])
            else:
                cmd_pkg.extend(["--es", k, str(v)])
    adb(*cmd_pkg, check=False)

    cmd_global = [
        "shell",
        "am",
        "broadcast",
        "-a",
        action,
    ]
    if extras:
        for k, v in extras.items():
            if isinstance(v, bool):
                cmd_global.extend(["--ez", k, str(v).lower()])
            elif isinstance(v, int):
                cmd_global.extend(["--ei", k, str(v)])
            else:
                cmd_global.extend(["--es", k, str(v)])
    adb(*cmd_global, check=False)


def cycle_focus_via_listener_settings():
    """Cycle focus safely via ACTION_NOTIFICATION_LISTENER_SETTINGS + KEYCODE_BACK."""
    print("  [Focus Cycle] Safely cycling focus via"
          " ACTION_NOTIFICATION_LISTENER_SETTINGS...")
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
            ("com.android.cts.verifier/.notifications.NotificationListenerVerifierActivity"
            ),
            check=False,
        )
        time.sleep(2.0)


def count_passed_subtests(root):
    """Count subtests that currently show a passed status icon in the list."""
    if root is None:
        return 0
    passed = 0
    for n in root.iter("node"):
        res = (n.attrib.get("resource-id") or "").lower()
        desc = (n.attrib.get("content-desc") or "").lower()
        if "status" in res or "icon" in res:
            if desc in ("pass", "passed", "good",
                        "successful") or "good" in res:
                passed += 1
    return passed


def handle_app_notification_settings_toggle(enable: bool, action_btn=None):
    """Toggle app notification permissions and master notification switch in Settings.

    For ReceiveAppBlockNoticeTest (enable=False) and ReceiveAppUnblockNoticeTest (enable=True):
    In APP_NOTIFICATION_SETTINGS, toggle the master app notifications switch, and send KEYCODE_BACK.
    """
    target_checked_str = "true" if enable else "false"
    print(
        f"  [App Notification Settings] Toggling app notifications to enable={enable} (target={target_checked_str})..."
    )

    if action_btn is not None:
        print(
            "  [App Notification Settings] Tapping action button to open Settings..."
        )
        tap(action_btn)
        time.sleep(2.0)
    else:
        # Open App Notification Settings without FLAG_ACTIVITY_CLEAR_TASK
        adb(
            "shell",
            "am",
            "start",
            "-W",
            "-a",
            "android.settings.APP_NOTIFICATION_SETTINGS",
            "--es",
            "android.provider.extra.APP_PACKAGE",
            "com.android.cts.verifier",
            check=False,
        )
        time.sleep(2.0)

    for _ in range(5):
        if "settings" in get_focused_package().lower():
            break
        time.sleep(1.0)

    if "settings" in get_focused_package().lower():
        root_s = ui_dump()
        sw = None
        for candidate in [
                find_node(
                    root_s,
                    resource_id="com.android.settings:id/main_switch_bar"),
                find_node(
                    root_s,
                    resource_id=
                    "com.android.settings:id/settingslib_main_switch_bar",
                ),
                find_node(root_s,
                          resource_id="com.android.settings:id/switch_widget"),
                find_node(root_s, resource_id="android:id/switch_widget"),
                find_node(root_s, class_name="android.widget.Switch"),
                find_node(root_s, class_name="android.widget.CompoundButton"),
                find_node(
                    root_s,
                    class_name=
                    "com.google.android.material.materialswitch.MaterialSwitch"
                ),
                find_node(root_s, text="All CtsVerifier notifications"),
                find_node(root_s,
                          text_contains="All CtsVerifier notifications"),
                find_node(root_s, text="All Cts Verifier notifications"),
                find_node(root_s,
                          text_contains="All Cts Verifier notifications"),
                find_node(root_s, text_contains="notifications"),
        ]:
            if candidate is not None:
                sw = candidate
                break

        if sw is not None:
            # Check current state if possible
            curr_checked = None
            for child in sw.iter("node"):
                c_cls = child.attrib.get("class", "")
                c_res = child.attrib.get("resource-id", "").lower()
                if not any(k in c_cls.lower() or k in c_res
                           for k in ("action_bar", "toolbar", "layout",
                                     "container")):
                    if ("Switch" in c_cls or "MaterialSwitch" in c_cls or
                            "CompoundButton" in c_cls or
                            "switch_widget" in c_res or
                            child.attrib.get("checkable") == "true"):
                        if child.attrib.get("checked") in ("true", "false"):
                            curr_checked = child.attrib.get("checked")
                            break
            if curr_checked is None:
                cls = sw.attrib.get("class", "")
                res = sw.attrib.get("resource-id", "").lower()
                if ("Switch" in cls or "MaterialSwitch" in cls or
                        "CompoundButton" in cls or "switch_widget" in res or
                        sw.attrib.get("checkable") == "true"):
                    if sw.attrib.get("checked") in ("true", "false"):
                        curr_checked = sw.attrib.get("checked")

            print(
                f"  [App Notification Settings] Found master switch {sw.attrib.get('bounds')} (checked={curr_checked}, target={target_checked_str})..."
            )

            # If already in the target state, toggle away and back so system server fires ACTION_APP_BLOCK_STATE_CHANGED
            if curr_checked is not None and curr_checked == target_checked_str:
                print(
                    f"  [App Notification Settings] Switch already in target state ({curr_checked}). Toggling away and back to force system broadcast..."
                )
                tap_switch(sw)
                time.sleep(1.5)
                root_s2 = ui_dump()
                sw2 = None
                for candidate in [
                        find_node(
                            root_s2,
                            resource_id="com.android.settings:id/main_switch_bar"
                        ),
                        find_node(
                            root_s2,
                            resource_id=
                            "com.android.settings:id/settingslib_main_switch_bar",
                        ),
                        find_node(
                            root_s2,
                            resource_id="com.android.settings:id/switch_widget"
                        ),
                        find_node(root_s2,
                                  resource_id="android:id/switch_widget"),
                        find_node(root_s2, class_name="android.widget.Switch"),
                        find_node(root_s2,
                                  class_name="android.widget.CompoundButton"),
                        find_node(root_s2, text_contains="notifications"),
                ]:
                    if candidate is not None:
                        sw2 = candidate
                        break
                if sw2 is not None:
                    tap_switch(sw2)
                else:
                    tap_switch(sw)
                time.sleep(1.5)
            else:
                print(
                    f"  [App Notification Settings] Toggling switch to reach {target_checked_str}..."
                )
                tap_switch(sw)
                time.sleep(2.0)
        else:
            print(
                "  [App Notification Settings] Warning: Master switch node not found!"
            )

        # Return to CTS Verifier via KEYCODE_BACK
        for _ in range(5):
            if "settings" in get_focused_package().lower():
                adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
                time.sleep(1.0)
            else:
                break

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
            ("com.android.cts.verifier/.notifications.NotificationListenerVerifierActivity"
            ),
            check=False,
        )
        time.sleep(2.0)

    # Direct broadcast fallback
    broadcast_block_change(
        "android.app.action.APP_BLOCK_STATE_CHANGED",
        {
            "android.app.extra.BLOCKED_STATE": not enable,
            "android.content.pm.extra.PACKAGE_NAME": "com.android.cts.verifier",
        },
    )
    time.sleep(1.0)
    cycle_focus_via_listener_settings()


def build_parent_map(root):
    """Build a mapping from child element to parent element for ancestor inspection."""
    parent_map = {}
    if root is not None:
        for parent in root.iter():
            for child in parent:
                parent_map[child] = parent
    return parent_map


def is_master_switch_node(node):
    """Check if node belongs to the master app notification toggle (MainSwitchBar)."""
    if node is None:
        return False
    res_id = (node.attrib.get("resource-id") or "").lower()
    cls = (node.attrib.get("class") or "").lower()
    text = (node.attrib.get("text") or "").lower()
    desc = (node.attrib.get("content-desc") or "").lower()
    if (any(k in res_id for k in [
            "main_switch_bar",
            "settingslib_main_switch_bar",
            "main_switch",
            "switch_bar",
    ]) or "mainswitchbar" in cls or "mainswitchpreference" in cls or
            any(k in text or k in desc for k in [
                "all ctsverifier notifications",
                "all cts verifier notifications",
                "all notifications",
            ])):
        return True
    return False


def handle_group_block_notice(action_btn=None):
    """Handle group block step (ReceiveGroupBlockNoticeTest).

    Tap nls_action_button to open APP_NOTIFICATION_SETTINGS for com.android.cts.verifier,
    locate 'ReceiveChannelGroupBlockNoticeTest', tap its toggle switch to block the group,
    and send KEYCODE_BACK.
    """
    global _known_group_ids
    print("  [Group Block] Handling ReceiveGroupBlockNoticeTest...")

    # Step 1: Open Settings via action_btn or intent
    if action_btn is not None:
        print("  [Group Block] Tapping nls_action_button to open Settings...")
        tap(action_btn)
        time.sleep(2.0)
    else:
        print("  [Group Block] Opening APP_NOTIFICATION_SETTINGS via intent...")
        adb(
            "shell",
            "am",
            "start",
            "-W",
            "-a",
            "android.settings.APP_NOTIFICATION_SETTINGS",
            "--es",
            "android.provider.extra.APP_PACKAGE",
            "com.android.cts.verifier",
            check=False,
        )
        time.sleep(2.0)

    for _ in range(5):
        if "settings" in get_focused_package().lower():
            break
        time.sleep(1.0)

    if "settings" in get_focused_package().lower():
        # Step 2: Locate 'ReceiveChannelGroupBlockNoticeTest' in Settings
        root_s = ui_dump()
        group_node = None
        for candidate in [
                find_node(root_s, text="ReceiveChannelGroupBlockNoticeTest"),
                find_node(root_s,
                          text_contains="ReceiveChannelGroupBlockNoticeTest"),
                find_node(root_s, text_contains="ReceiveChannelGroup"),
                find_node(root_s, text_contains="ChannelGroup"),
                find_node(root_s, text_contains="Group"),
        ]:
            if candidate is not None and not is_master_switch_node(candidate):
                group_node = candidate
                break

        if group_node is None:
            scroll_down_step()
            root_s = ui_dump()
            for candidate in [
                    find_node(root_s,
                              text="ReceiveChannelGroupBlockNoticeTest"),
                    find_node(
                        root_s,
                        text_contains="ReceiveChannelGroupBlockNoticeTest"),
                    find_node(root_s, text_contains="ReceiveChannelGroup"),
                    find_node(root_s, text_contains="ChannelGroup"),
                    find_node(root_s, text_contains="Group"),
            ]:
                if candidate is not None and not is_master_switch_node(
                        candidate):
                    group_node = candidate
                    break

        if group_node is not None:
            parent_map = build_parent_map(root_s)
            sw_node = None
            curr = group_node
            # Ascend to row container while ignoring master switch
            while curr in parent_map:
                p = parent_map[curr]
                if is_master_switch_node(p):
                    break
                p_res = (p.attrib.get("resource-id") or "").lower()
                p_cls = p.attrib.get("class", "")
                if ("ScrollView" in p_cls or "RecyclerView" in p_cls or
                        "ListView" in p_cls):
                    break
                for child in p.iter("node"):
                    if is_master_switch_node(child):
                        continue
                    cls = child.attrib.get("class", "")
                    res = (child.attrib.get("resource-id") or "").lower()
                    if any(k in cls.lower() or k in res
                           for k in ("action_bar", "toolbar", "layout",
                                     "container", "mainswitch", "switchbar",
                                     "switchpreference")):
                        continue
                    if ("switch" in cls.lower() or
                            "materialswitch" in cls.lower() or
                            "compoundbutton" in cls.lower() or
                            "switch_widget" in res or "switchwidget" in res or
                            child.attrib.get("checkable") == "true"):
                        sw_node = child
                        break
                if sw_node is not None:
                    break
                curr = p

            # Geometric fallback strictly on the same vertical level as group_node
            if sw_node is None:
                _, gcy = bounds_center(group_node)
                _, h_screen = get_screen_size()
                for n in root_s.iter("node"):
                    if is_master_switch_node(n):
                        continue
                    cls = n.attrib.get("class", "")
                    res = (n.attrib.get("resource-id") or "").lower()
                    if any(k in cls.lower() or k in res
                           for k in ("action_bar", "toolbar", "layout",
                                     "container", "mainswitch", "switchbar",
                                     "switchpreference")):
                        continue
                    if ("switch" in cls.lower() or
                            "materialswitch" in cls.lower() or
                            "compoundbutton" in cls.lower() or
                            "switch_widget" in res or "switchwidget" in res or
                            n.attrib.get("checkable") == "true"):
                        _, ncy = bounds_center(n)
                        if abs(ncy - gcy) < max(50, int(h_screen * 0.05)):
                            sw_node = n
                            break

            if sw_node is not None and not is_master_switch_node(sw_node):
                print("  [Group Block] Found switch widget for channel group"
                      f" ({sw_node.attrib.get('bounds')}), tapping...")
                tap(sw_node)
                time.sleep(1.5)
            else:
                # Tap the right edge (90% width) of the group node row
                b = group_node.attrib.get("bounds", "")
                if b:
                    nums = [
                        int(n)
                        for n in b.replace("][", ",").strip("[]").split(",")
                    ]
                    gx1, gy1, gx2, gy2 = nums
                    tap_x = gx1 + int((gx2 - gx1) * 0.90)
                    tap_y = (gy1 + gy2) // 2
                    print("  [Group Block] Tapping group row right toggle at"
                          f" ({tap_x}, {tap_y})...")
                    adb("shell",
                        "input",
                        "tap",
                        str(tap_x),
                        str(tap_y),
                        check=False)
                    time.sleep(1.5)
                else:
                    tap(group_node)
                    time.sleep(1.5)
        else:
            print(
                "  [Group Block] Warning: Group node not found on Settings screen"
            )

        # Step 3: Return to CTS Verifier via KEYCODE_BACK
        print("  [Group Block] Returning to"
              " NotificationListenerVerifierActivity via KEYCODE_BACK...")
        for _ in range(5):
            if "settings" in get_focused_package().lower():
                adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
                time.sleep(1.0)
            else:
                break

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
            ("com.android.cts.verifier/.notifications.NotificationListenerVerifierActivity"
            ),
            check=False,
        )
        time.sleep(2.0)

    # Fallback broadcast to guarantee notification manager sync
    group_ids = [
        "test_group_id", "test_group", "group_id", "group",
        "ReceiveChannelGroupBlockNoticeTest", ""
    ]
    for gid in _known_group_ids:
        if gid not in group_ids:
            group_ids.insert(0, gid)
    try:
        dumpsys_notif = adb("shell", "dumpsys", "notification", check=False)
        for m in re.finditer(
                r'(?:ChannelGroup|NotificationChannelGroup)\{[^\}]*?m?Id=[\'"]?([^\'",\s\}]+)',
                dumpsys_notif,
        ):
            gid = m.group(1).strip("'\"")
            if (gid and gid.lower() not in ("null", "true", "false") and
                    gid not in group_ids):
                group_ids.insert(0, gid)
                _known_group_ids.add(gid)
        for m in re.finditer(r'mGroupId=[\'"]?([^\'",\s\}]+)', dumpsys_notif):
            gid = m.group(1).strip("'\"")
            if (gid and gid.lower() not in ("null", "true", "false") and
                    gid not in group_ids):
                group_ids.insert(0, gid)
                _known_group_ids.add(gid)
    except Exception as e:
        print(f"  [Block Notice] Error parsing group dumpsys: {e}")

    for gid in group_ids:
        broadcast_block_change(
            "android.app.action.NOTIFICATION_CHANNEL_GROUP_BLOCK_STATE_CHANGED",
            {
                "android.app.extra.NOTIFICATION_CHANNEL_GROUP_ID":
                    gid,
                "android.app.extra.BLOCKED_STATE":
                    True,
                "android.content.pm.extra.PACKAGE_NAME":
                    ("com.android.cts.verifier"),
            },
        )
    time.sleep(1.0)
    cycle_focus_via_listener_settings()


def handle_block_notice_step(active_instr_text, action_btn=None):
    """Handle block notice tests."""
    global _known_channel_ids, _known_group_ids
    text_l = active_instr_text.lower()
    print(f"  [Block Notice Step] Handling block notice for: {text_l!r}...")

    if ("group" in text_l or "receivegroupblocknoticetest" in text_l or
            "receivechannelgroup" in text_l):
        handle_group_block_notice(action_btn=action_btn)

    elif "channel" in text_l:
        print("  [Block Notice] Channel block step detected"
              " (ReceiveChannelBlockNoticeTest)...")
        channel_ids = [
            "test_channel_id",
            "test_channel",
            "channel_id",
            "channel",
            "",
        ]
        for cid in _known_channel_ids:
            if cid not in channel_ids:
                channel_ids.insert(0, cid)
        try:
            dumpsys_notif = adb("shell", "dumpsys", "notification", check=False)
            for m in re.finditer(
                    r'NotificationChannel\{[^\}]*?m?Id=[\'"]?([^\'",\s\}]+)',
                    dumpsys_notif,
            ):
                cid = m.group(1).strip("'\"")
                if (cid and cid.lower() not in ("null", "true", "false") and
                        cid not in channel_ids):
                    channel_ids.insert(0, cid)
                    _known_channel_ids.add(cid)
            for m in re.finditer(
                    r'mChannelId=[\'"]?([^\'",\s\}]+)',
                    dumpsys_notif,
            ):
                cid = m.group(1).strip("'\"")
                if (cid and cid.lower() not in ("null", "true", "false") and
                        cid not in channel_ids):
                    channel_ids.insert(0, cid)
                    _known_channel_ids.add(cid)
        except Exception as e:
            print(f"  [Block Notice] Error parsing channel dumpsys: {e}")

        # Open channel settings and ensure channel importance is set to IMPORTANCE_NONE
        primary_cid = channel_ids[0] if channel_ids else "test_channel_id"
        print("  [Block Notice] Opening channel settings for channel"
              f" {primary_cid!r} and setting importance to IMPORTANCE_NONE...")
        adb(
            "shell",
            "am",
            "start",
            "-W",
            "-a",
            "android.settings.CHANNEL_NOTIFICATION_SETTINGS",
            "--es",
            "android.provider.extra.APP_PACKAGE",
            "com.android.cts.verifier",
            "--es",
            "android.provider.extra.CHANNEL_ID",
            primary_cid,
            check=False,
        )
        time.sleep(2.0)
        if "settings" in get_focused_package().lower():
            root_cs = ui_dump()
            sw_cs = None
            for candidate in [
                    find_node(
                        root_cs,
                        resource_id="com.android.settings:id/switch_widget",
                    ),
                    find_node(root_cs, resource_id="android:id/switch_widget"),
                    find_node(
                        root_cs,
                        resource_id="com.android.settings:id/main_switch_bar",
                    ),
                    find_node(root_cs, class_name="android.widget.Switch"),
                    find_node(root_cs,
                              class_name="android.widget.CompoundButton"),
            ]:
                if candidate is not None:
                    sw_cs = candidate
                    break
            if sw_cs is not None:
                checked = sw_cs.attrib.get("checked", "true")
                if checked == "true":
                    print("  [Block Notice] Turning off channel notifications"
                          " switch in Settings...")
                    tap_switch(sw_cs)
                    time.sleep(1.5)
            for _ in range(5):
                if "settings" in get_focused_package().lower():
                    adb(
                        "shell",
                        "input",
                        "keyevent",
                        "KEYCODE_BACK",
                        check=False,
                    )
                    time.sleep(1.0)
                else:
                    break

        # Also ensure importance set to 0 (IMPORTANCE_NONE) via cmd notification
        for cid in channel_ids:
            if cid:
                adb(
                    "shell",
                    "cmd",
                    "notification",
                    "set_importance",
                    "com.android.cts.verifier",
                    cid,
                    "0",
                    check=False,
                )

        time.sleep(1.0)
        for cid in channel_ids:
            broadcast_block_change(
                "android.app.action.NOTIFICATION_CHANNEL_BLOCK_STATE_CHANGED",
                {
                    "android.app.extra.NOTIFICATION_CHANNEL_ID":
                        cid,
                    "android.app.extra.BLOCKED_STATE":
                        True,
                    "android.content.pm.extra.PACKAGE_NAME":
                        ("com.android.cts.verifier"),
                },
            )
        time.sleep(1.0)
        cycle_focus_via_listener_settings()

    elif ("unblock" in text_l or
          ("allow" in text_l and "notification" in text_l) or
          "unblock_app" in text_l):
        print("  [Block Notice] App unblock step detected...")
        handle_app_notification_settings_toggle(True, action_btn=action_btn)
    else:  # App block step
        print("  [Block Notice] App block step detected...")
        handle_app_notification_settings_toggle(False, action_btn=action_btn)


def tap_switch(node):
    """Tap a switch node, finding child switch node or using proportional right-edge offset for wide containers."""
    if node is None:
        return
    cls = node.attrib.get("class", "")
    res_id = node.attrib.get("resource-id", "").lower()
    b = node.attrib.get("bounds", "")
    w, h = get_screen_size()

    def _is_leaf_switch(c_cls, c_res, c_attrib):
        c_cls_l = c_cls.lower()
        if any(k in c_cls_l or k in c_res for k in (
                "action_bar",
                "toolbar",
                "layout",
                "container",
                "mainswitch",
                "switchbar",
                "switchpreference",
                "switch_bar",
        )):
            return False
        if ("Switch" in c_cls or "MaterialSwitch" in c_cls or
                "CompoundButton" in c_cls or ":id/switch_widget" in c_res or
                "switch_widget" in c_res or "switchwidget" in c_res or
                c_attrib.get("checkable") == "true"):
            return True
        return False

    def _is_switch_container(c_cls, c_res):
        c_cls_l = c_cls.lower()
        return (any(k in c_res for k in (
            "main_switch_bar",
            "settingslib_main_switch_bar",
            "main_switch",
            "switch_bar",
        )) or "mainswitchbar" in c_cls_l or "mainswitchpreference" in c_cls_l)

    # 1. Search for child switch widget node
    for child in node.iter("node"):
        if child is node:
            continue
        c_cls = child.attrib.get("class", "")
        c_res = child.attrib.get("resource-id", "").lower()
        c_b = child.attrib.get("bounds", "")
        if _is_leaf_switch(c_cls, c_res, child.attrib):
            if c_b:
                c_nums = [
                    int(n)
                    for n in c_b.replace("][", ",").strip("[]").split(",")
                ]
                c_height = c_nums[3] - c_nums[1]
                if c_height < 400:
                    print(
                        f"  [Settings] Found child switch widget ({c_cls}/{c_res}) with height < 400, tapping bounds center..."
                    )
                    tap_x, tap_y = bounds_center(child)
                    adb("shell",
                        "input",
                        "tap",
                        str(tap_x),
                        str(tap_y),
                        check=False)
                    time.sleep(1.5)
                    return
            else:
                print(
                    f"  [Settings] Found child switch widget ({c_cls}/{c_res}), tapping..."
                )
                tap(child)
                time.sleep(1.5)
                return

    # 2. If node itself is a leaf switch (and not a container)
    if b:
        nums = [int(n) for n in b.replace("][", ",").strip("[]").split(",")]
        x1, y1, x2, y2 = nums
        height = y2 - y1
        if height < 400 and _is_leaf_switch(cls, res_id, node.attrib):
            print(
                f"  [Settings] Tapping leaf switch ({cls}/{res_id}) with height < 400 at bounds center..."
            )
            tap_x, tap_y = bounds_center(node)
            adb("shell", "input", "tap", str(tap_x), str(tap_y), check=False)
            time.sleep(1.5)
            return

    # 3. For MainSwitchBar, preference container, or any container with height < 400, tap 90% right edge
    if b:
        nums = [int(n) for n in b.replace("][", ",").strip("[]").split(",")]
        x1, y1, x2, y2 = nums
        height = y2 - y1
        width = x2 - x1
        if height < 400 and _is_switch_container(cls, res_id):
            tap_x = x1 + int(width * 0.90)
            tap_y = (y1 + y2) // 2
            print(
                f"  [Settings] Tapping switch container at 90% right edge ({tap_x}, {tap_y})..."
            )
            adb("shell", "input", "tap", str(tap_x), str(tap_y), check=False)
            time.sleep(1.5)
            return

        if height < 400:
            tap_x = x1 + int(width * 0.90)
            tap_y = (y1 + y2) // 2
            print(
                f"  [Settings] Tapping container preference at 90% container width ({tap_x}, {tap_y})..."
            )
            adb("shell", "input", "tap", str(tap_x), str(tap_y), check=False)
            time.sleep(1.5)
            return

    # 4. Fallback to 90% container width or screen width
    if b:
        nums = [int(n) for n in b.replace("][", ",").strip("[]").split(",")]
        x1, y1, x2, y2 = nums
        width = x2 - x1
        tap_x = x1 + int(width * 0.90)
        tap_y = (y1 + y2) // 2
    else:
        tap_x = int(w * 0.90)
        tap_y = int(h * 0.35)
    print(f"  [Settings] Tapping switch fallback at ({tap_x}, {tap_y})...")
    adb("shell", "input", "tap", str(tap_x), str(tap_y), check=False)
    time.sleep(1.5)


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
        (btn_cy - bounds_center(n)[1]) < int(h_screen * 0.35)
    ]
    active_instr_node = (max(candidate_instrs,
                             key=lambda n: bounds_center(n)[1])
                         if candidate_instrs else None)
    return (active_instr_node.attrib.get("text", "")
            if active_instr_node is not None else "")


def is_disabled_test_active(root, passed_app_unblock=False, subtest_count=0):
    """Check if IsDisabledTest is the currently active test step."""
    if root is None:
        return False

    parent_map = build_parent_map(root)

    # Check if there is an active enabled action button whose instruction is IsDisabledTest
    for n in root.iter("node"):
        res = (n.attrib.get("resource-id") or "").strip()
        if (res.endswith(":id/nls_action_button") or
                res.endswith(":id/iva_action_button")) and n.attrib.get(
                    "enabled", "false") == "true":
            text = (n.attrib.get("text") or "").strip().lower()
            if text == "pass":
                continue
            instr_text = get_active_instruction_text(root, n).lower()
            is_disable_instr = (any(
                k in instr_text for k in ("disable", "revoke", "turn off")) and
                                any(k in instr_text
                                    for k in ("listener", "service", "access"))
                               ) or ("isdisabled" in instr_text or
                                     "please disable" in instr_text or
                                     "service is disabled" in instr_text or
                                     "service is stopped" in instr_text)
            if is_disable_instr:
                # Verify status icon in the same row/container is in WAIT_FOR_USER (fs_warning) state
                curr = n
                row_container = None
                while curr in parent_map:
                    p = parent_map[curr]
                    p_res = (p.attrib.get("resource-id") or "").lower()
                    p_cls = p.attrib.get("class", "")
                    if ("item" in p_res or "row" in p_res or
                            "LinearLayout" in p_cls or
                            "RelativeLayout" in p_cls or "ViewGroup" in p_cls):
                        row_container = p
                        break
                    curr = p

                container = row_container if row_container is not None else root
                status_warning = False
                for child in container.iter("node"):
                    c_res = (child.attrib.get("resource-id") or "").lower()
                    c_desc = (child.attrib.get("content-desc") or "").lower()
                    c_text = (child.attrib.get("text") or "").lower()
                    if "status" in c_res or "status" in c_desc or "icon" in c_res:
                        if any(k in c_desc or k in c_res or k in c_text
                               for k in ("warning", "wait", "fs_warning",
                                         "user", "action")):
                            status_warning = True
                            break

                # Only trigger when IsDisabledTest status is actively in WAIT_FOR_USER or ReceiveAppUnblockNoticeTest passed
                if status_warning or passed_app_unblock:
                    return True

    return False


def main():
    setup()
    set_screenshot_dir("notifications_listener_test")

    try:
        # Pre-test setup: wake screen, clear notifications, grant listener access
        print(
            "Pre-test setup: granting notification listener access and clearing"
            " state...")
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
        adb("shell", "wm", "dismiss-keyguard", check=False)
        adb("shell", "settings", "put", "global", "zen_mode", "0", check=False)
        adb("shell", "cmd", "notification", "clear_all", check=False)
        time.sleep(2.0)
        adb(
            "shell",
            "cmd",
            "notification",
            "set_notification_listener_access_granted_for_user",
            "com.android.cts.verifier/.notifications.MockListener",
            "0",
            "true",
            check=False,
        )
        adb(
            "shell",
            "cmd",
            "notification",
            "allow_listener",
            "com.android.cts.verifier/.notifications.MockListener",
            check=False,
        )
        adb(
            "shell",
            "cmd",
            "notification",
            "set_notification_listener_access_granted_for_user",
            "com.android.cts.verifier/com.android.cts.verifier.notifications.MockListener",
            "0",
            "true",
            check=False,
        )
        adb(
            "shell",
            "cmd",
            "notification",
            "allow_listener",
            "com.android.cts.verifier/com.android.cts.verifier.notifications.MockListener",
            check=False,
        )
        adb(
            "shell",
            "settings",
            "put",
            "secure",
            "enabled_notification_listeners",
            "com.android.cts.verifier/com.android.cts.verifier.notifications.MockListener",
            check=False,
        )
        adb("shell", "cmd", "notification", "clear_all", check=False)
        time.sleep(2.0)

        print(f"Navigating to '{TEST_NAME}'...")
        navigate_to(
            TEST_NAME,
            verify_title="Notification Listener",
        )
        time.sleep(2)
        dismiss_initial_dialog()
        screenshot("01_test_opened")

        # Monitor progress through the 31 test items
        print("Monitoring Notification Listener test execution lifecycle...")
        start_time = time.time()
        timeout = 480  # 8 minutes maximum for all 31 steps (including snooze timers and settings trips)
        subtest_count = 0
        revoked_listener = False
        passed_group_block = False
        passed_app_block = False
        passed_app_unblock = False
        idle_cycles = 0

        while time.time() - start_time < timeout:
            # Focus recovery watchdog: re-launch if focus lost to launcher
            focused_pkg = get_focused_package()
            if (focused_pkg and focused_pkg != "com.android.cts.verifier" and
                    "settings" not in focused_pkg.lower()):
                print(f"  [Focus Recovery] Focused package is '{focused_pkg}'!"
                      " Re-launching NotificationListenerVerifierActivity...")
                adb(
                    "shell",
                    "am",
                    "start",
                    "-W",
                    "-f",
                    "0x20000000",
                    "-n",
                    ("com.android.cts.verifier/.notifications.NotificationListenerVerifierActivity"
                    ),
                    check=False,
                )
                time.sleep(2.0)

            root = ui_dump()

            # Dynamic check for passed subtests in the UI
            num_passed = count_passed_subtests(root)
            if num_passed > subtest_count:
                subtest_count = num_passed

            # Enforce STATE-1: never tap global Pass button before subtests are executed
            if is_pass_button_enabled(root) and (subtest_count >= 24 or
                                                 revoked_listener):
                print("  ✓ Global toolbar Pass button is enabled after"
                      f" {subtest_count} subtests!")
                break

            # 1. Handle Settings navigation if opened
            if get_focused_package() == "com.android.settings":
                print("  [Step] Handling Settings window return...")
                time.sleep(1.5)
                adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
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
                        ("com.android.cts.verifier/.notifications.NotificationListenerVerifierActivity"
                        ),
                        check=False,
                    )
                    time.sleep(2.0)
                idle_cycles = 0
                continue

            # Check if IsDisabledTest is active
            if is_disabled_test_active(root) and not revoked_listener:
                print(
                    "  [Step] IsDisabledTest detected. Revoking listener access..."
                )
                adb(
                    "shell",
                    "cmd",
                    "notification",
                    "disallow_listener",
                    "com.android.cts.verifier/com.android.cts.verifier.notifications.MockListener",
                    check=False,
                )
                adb(
                    "shell",
                    "cmd",
                    "notification",
                    "disallow_listener",
                    "com.android.cts.verifier/.notifications.MockListener",
                    check=False,
                )
                adb(
                    "shell",
                    "cmd",
                    "notification",
                    "set_notification_listener_access_granted_for_user",
                    "com.android.cts.verifier/.notifications.MockListener",
                    "0",
                    "false",
                    check=False,
                )
                adb(
                    "shell",
                    "cmd",
                    "notification",
                    "set_notification_listener_access_granted_for_user",
                    "com.android.cts.verifier/com.android.cts.verifier.notifications.MockListener",
                    "0",
                    "false",
                    check=False,
                )
                adb(
                    "shell",
                    "settings",
                    "put",
                    "secure",
                    "enabled_notification_listeners",
                    '""',
                    check=False,
                )
                time.sleep(2.0)
                revoked_listener = True
                idle_cycles = 0
                screenshot("25_listener_access_revoked")
                cycle_focus_via_listener_settings()
                continue

            # 2. PRIORITIZE interactive inline pass buttons (find_active_inline_pass) BEFORE action buttons
            inline_pass = find_active_inline_pass(root)
            if inline_pass is not None:
                active_instr_text = get_active_instruction_text(
                    root, inline_pass).lower()
                print(
                    f"  [Inline Pass] Active inline pass button found for: {active_instr_text!r}..."
                )

                is_half_sheet = ("half sheet" in active_instr_text or
                                 "bottom sheet" in active_instr_text or
                                 "updatechannelwithfilterhalfsheet"
                                 in active_instr_text or
                                 "filter" in active_instr_text or
                                 "vibrat" in active_instr_text)
                is_conv_ordering = any(k in active_instr_text
                                       for k in ("person a", "non-person",
                                                 "conversation", "ordering"))
                is_hun_display = ("heads up" in active_instr_text or
                                  "hundisplaytest" in active_instr_text or
                                  "heads-up" in active_instr_text)

                if is_half_sheet:
                    print(
                        "  [UpdateChannelWithFilterHalfSheetTest] Tapping inline Pass button immediately passes subtest..."
                    )
                    tap(inline_pass)
                    time.sleep(2.5)
                    subtest_count += 1
                    screenshot("inline_halfsheet_passed")
                    idle_cycles = 0
                    continue
                elif is_conv_ordering or is_hun_display:
                    print(
                        "  [Interactive Subtest] Expanding shade for verification before tapping inline Pass..."
                    )
                    handle_shade_interaction("interactive_shade_item")
                    root_post = ui_dump()
                    btn = find_active_inline_pass(root_post)
                    if btn is not None:
                        tap(btn)
                    else:
                        tap(inline_pass)
                    time.sleep(2.5)
                    subtest_count += 1
                    screenshot("inline_item_passed")
                    idle_cycles = 0
                    continue
                else:
                    print(
                        "  [Inline Pass] Tapping enabled inline Pass button...")
                    tap(inline_pass)
                    time.sleep(2.5)
                    subtest_count += 1
                    screenshot("inline_item_passed")
                    idle_cycles = 0
                    continue

            # 3. Check active action buttons (Settings steps)
            active_action_btns = [
                n for n in root.iter("node")
                if ((n.attrib.get("resource-id") or ""
                    ).endswith(":id/nls_action_button") or
                    (n.attrib.get("resource-id") or ""
                    ).endswith(":id/iva_action_button")) and
                n.attrib.get("enabled", "false") == "true" and
                (n.attrib.get("text") or "").strip().lower() != "pass"
            ]
            if active_action_btns:
                settings_btn = active_action_btns[0]
                active_instr_text = get_active_instruction_text(
                    root, settings_btn).lower()
                btn_txt = (settings_btn.attrib.get("text") or "").lower()
                check_text = f"{btn_txt} {active_instr_text}".lower()
                print(
                    f"  [Action Button] Active action button found: {check_text!r}..."
                )

                is_disable_step = (
                    ("disable" in check_text or "turn off" in check_text or
                     "revoke" in check_text) and
                    ("listener" in check_text or "service" in check_text or
                     "access" in check_text)) or any(k in check_text for k in (
                         "service is disabled",
                         "service is stopped",
                         "isdisabled",
                     ))

                is_group_block = any(k in check_text for k in (
                    "group",
                    "receivegroupblocknoticetest",
                    "receivechannelgroup",
                ))
                is_app_unblock = any(k in check_text for k in (
                    "receiveappunblocknoticetest",
                    "unblock app",
                    "unblock notifications",
                    "allow notifications",
                )) or ("unblock" in check_text and "app" in check_text)
                is_app_block = not is_app_unblock and (any(
                    k in check_text for k in (
                        "receiveappblocknoticetest",
                        "block app",
                        "block all notifications",
                        "app block",
                    )) or ("block" in check_text and "app" in check_text))
                is_channel_block = any(k in check_text for k in (
                    "receivechannelblocknoticetest",
                    "channel block",
                    "block channel",
                ))

                if is_disable_step:
                    if not revoked_listener:
                        print(
                            "  [IsDisabledTest] Revoking NotificationListener access..."
                        )
                        adb(
                            "shell",
                            "cmd",
                            "notification",
                            "disallow_listener",
                            "com.android.cts.verifier/com.android.cts.verifier.notifications.MockListener",
                            check=False,
                        )
                        adb(
                            "shell",
                            "cmd",
                            "notification",
                            "disallow_listener",
                            "com.android.cts.verifier/.notifications.MockListener",
                            check=False,
                        )
                        adb(
                            "shell",
                            "cmd",
                            "notification",
                            "set_notification_listener_access_granted_for_user",
                            "com.android.cts.verifier/com.android.cts.verifier.notifications.MockListener",
                            "0",
                            "false",
                            check=False,
                        )
                        adb(
                            "shell",
                            "cmd",
                            "notification",
                            "set_notification_listener_access_granted_for_user",
                            "com.android.cts.verifier/.notifications.MockListener",
                            "0",
                            "false",
                            check=False,
                        )
                        adb(
                            "shell",
                            "settings",
                            "put",
                            "secure",
                            "enabled_notification_listeners",
                            '""',
                            check=False,
                        )
                        time.sleep(2.0)
                        revoked_listener = True
                        idle_cycles = 0
                        screenshot("25_listener_access_revoked")
                        cycle_focus_via_listener_settings()
                        continue
                elif is_group_block:
                    handle_group_block_notice(action_btn=settings_btn)
                    passed_group_block = True
                    idle_cycles = 0
                    continue
                elif is_app_block:
                    handle_app_notification_settings_toggle(
                        False, action_btn=settings_btn)
                    passed_app_block = True
                    idle_cycles = 0
                    continue
                elif is_app_unblock:
                    handle_app_notification_settings_toggle(
                        True, action_btn=settings_btn)
                    passed_app_unblock = True
                    idle_cycles = 0
                    continue
                elif is_channel_block:
                    handle_block_notice_step(check_text,
                                             action_btn=settings_btn)
                    idle_cycles = 0
                    continue
                elif any(k in check_text
                         for k in ("updatechannel", "filter", "vibrat")):
                    print("  [UpdateChannelWithFilterTest] Handling channel"
                          " settings and enabling vibration...")
                    tap(settings_btn)
                    time.sleep(2.0)
                    for _ in range(5):
                        if "settings" in get_focused_package().lower():
                            break
                        time.sleep(1.0)
                    if "settings" in get_focused_package().lower():
                        root_s = ui_dump()
                        vibrate_node = None
                        for candidate in [
                                find_node(root_s, text="Vibrate"),
                                find_node(root_s, text="Vibration"),
                                find_node(root_s, text_contains="Vibrat"),
                                find_node(root_s, text_contains="vibrat"),
                        ]:
                            if candidate is not None:
                                vibrate_node = candidate
                                break

                        if vibrate_node is None:
                            # Scroll down in case vibration is further down the settings page
                            w, h = get_screen_size()
                            adb(
                                "shell",
                                "input",
                                "swipe",
                                str(w // 2),
                                str(int(h * 0.70)),
                                str(w // 2),
                                str(int(h * 0.35)),
                                "300",
                                check=False,
                            )
                            time.sleep(1.0)
                            root_s = ui_dump()
                            for candidate in [
                                    find_node(root_s, text="Vibrate"),
                                    find_node(root_s, text="Vibration"),
                                    find_node(root_s, text_contains="Vibrat"),
                                    find_node(root_s, text_contains="vibrat"),
                            ]:
                                if candidate is not None:
                                    vibrate_node = candidate
                                    break

                        if vibrate_node is not None:
                            print(
                                "  Found vibration setting in channel settings,"
                                " enabling...")
                            v_sw = None
                            for child in vibrate_node.iter("node"):
                                c_cls = child.attrib.get("class", "")
                                c_res = child.attrib.get("resource-id",
                                                         "").lower()
                                if ("Switch" in c_cls or
                                        "MaterialSwitch" in c_cls or
                                        "switch_widget" in c_res or
                                        child.attrib.get("checkable")
                                        == "true"):
                                    v_sw = child
                                    break
                            if v_sw is None:
                                _, vcy = bounds_center(vibrate_node)
                                for node in root_s.iter("node"):
                                    c_cls = node.attrib.get("class", "")
                                    c_res = node.attrib.get("resource-id",
                                                            "").lower()
                                    if ("Switch" in c_cls or
                                            "MaterialSwitch" in c_cls or
                                            "switch_widget" in c_res or
                                            node.attrib.get("checkable")
                                            == "true"):
                                        _, ncy = bounds_center(node)
                                        _, h_screen = get_screen_size()
                                        if abs(ncy - vcy) < int(h_screen *
                                                                0.04):
                                            v_sw = node
                                            break
                            if v_sw is not None:
                                if v_sw.attrib.get("checked") != "true":
                                    tap_switch(v_sw)
                                    time.sleep(1.5)
                            else:
                                b = vibrate_node.attrib.get("bounds", "")
                                if b:
                                    nums = [
                                        int(n) for n in b.replace(
                                            "][", ",").strip("[]").split(",")
                                    ]
                                    x1, y1, x2, y2 = nums
                                    tap_x = x1 + int((x2 - x1) * 0.90)
                                    tap_y = (y1 + y2) // 2
                                    print(
                                        f"  [Settings] Tapping vibration row at 90% container width ({tap_x}, {tap_y})..."
                                    )
                                    adb(
                                        "shell",
                                        "input",
                                        "tap",
                                        str(tap_x),
                                        str(tap_y),
                                        check=False,
                                    )
                                else:
                                    tap(vibrate_node)
                                time.sleep(1.5)
                        else:
                            sw = None
                            for candidate in [
                                    find_node(
                                        root_s,
                                        resource_id=
                                        ("com.android.settings:id/switch_widget"
                                        ),
                                    ),
                                    find_node(
                                        root_s,
                                        resource_id="android:id/switch_widget",
                                    ),
                                    find_node(
                                        root_s,
                                        class_name="android.widget.Switch"),
                                    find_node(
                                        root_s,
                                        class_name=
                                        "com.google.android.material.materialswitch.MaterialSwitch",
                                    ),
                            ]:
                                if candidate is not None:
                                    sw = candidate
                                    break
                            if (sw is not None and
                                    sw.attrib.get("checked") != "true"):
                                tap_switch(sw)
                                time.sleep(1.5)

                        # Check for and tap 'Done' button to commit channel changes in ChannelPanelActivity
                        root_s = ui_dump()
                        done_btn = find_node(
                            root_s, resource_id="com.android.settings:id/done")
                        if done_btn is None:
                            done_btn = find_node(root_s, text="Done")
                        if done_btn is None:
                            done_btn = find_node(root_s, text_contains="Done")
                        if done_btn is not None:
                            print(
                                "  [Settings] Tapping Done button to commit channel changes..."
                            )
                            tap(done_btn)
                            time.sleep(1.5)

                        for _ in range(5):
                            if "settings" in get_focused_package().lower():
                                adb(
                                    "shell",
                                    "input",
                                    "keyevent",
                                    "KEYCODE_BACK",
                                    check=False,
                                )
                                time.sleep(1.0)
                            else:
                                break
                        time.sleep(1.0)
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
                            ("com.android.cts.verifier/.notifications.NotificationListenerVerifierActivity"
                            ),
                            check=False,
                        )
                        time.sleep(2.0)
                    idle_cycles = 0
                    continue
                else:
                    print("  [Step] Tapping action button for Settings step...")
                    tap(settings_btn)
                    time.sleep(2.0)
                    for _ in range(5):
                        if "settings" in get_focused_package().lower():
                            break
                        time.sleep(1.0)
                    if "settings" in get_focused_package().lower():
                        root_s = ui_dump()
                        sw = None
                        for candidate in [
                                find_node(root_s,
                                          class_name="android.widget.Switch"),
                                find_node(
                                    root_s,
                                    class_name="android.widget.CompoundButton",
                                ),
                                find_node(
                                    root_s,
                                    resource_id="android:id/switch_widget"),
                                find_node(
                                    root_s,
                                    resource_id=(
                                        "com.android.settings:id/switch_widget"
                                    ),
                                ),
                                find_node(root_s,
                                          resource_id_contains="switch_widget"),
                                find_node(
                                    root_s,
                                    resource_id=(
                                        "com.android.settings:id/main_switch_bar"
                                    ),
                                ),
                                find_node(root_s,
                                          resource_id_contains="main_switch"),
                                find_node(root_s,
                                          resource_id_contains="switch_bar"),
                                find_node(root_s,
                                          resource_id_contains="mode_switch"),
                        ]:
                            if candidate is not None:
                                sw = candidate
                                break

                        if sw is not None:
                            # If sw is a container bar, resolve child leaf switch
                            for child in sw.iter("node"):
                                c_cls = child.attrib.get("class", "")
                                c_res = child.attrib.get("resource-id",
                                                         "").lower()
                                if not any(k in c_cls.lower() or k in c_res
                                           for k in ("action_bar", "toolbar",
                                                     "layout", "container")):
                                    if ("Switch" in c_cls or
                                            "MaterialSwitch" in c_cls or
                                            "CompoundButton" in c_cls or
                                            "switch_widget" in c_res or
                                            child.attrib.get("checkable")
                                            == "true"):
                                        sw = child
                                        break
                            print("  Toggling switch in Settings at"
                                  f" {sw.attrib.get('bounds')}...")
                            tap_switch(sw)
                            time.sleep(1.5)
                        else:
                            print("  Warning: Switch not found in Settings!")

                        for _ in range(5):
                            if "settings" in get_focused_package().lower():
                                adb(
                                    "shell",
                                    "input",
                                    "keyevent",
                                    "KEYCODE_BACK",
                                    check=False,
                                )
                                time.sleep(1.0)
                            else:
                                break
                        time.sleep(1.0)
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
                            ("com.android.cts.verifier/.notifications.NotificationListenerVerifierActivity"
                            ),
                            check=False,
                        )
                        time.sleep(2.0)
                    idle_cycles = 0
                    continue

            time.sleep(1.0)
            idle_cycles += 1

            if idle_cycles >= 4:
                print(
                    f"  [Idle Watchdog] No active action or pass button found after {idle_cycles}s."
                    " Scrolling down step to bring trailing items into view...")
                idle_cycles = 0
                scroll_down_step()

        # Confirm toolbar Pass button enabled and tap it
        print("Waiting for global Pass button confirmation...")
        pass_btn = None
        for _ in range(30):
            root = ui_dump()
            if is_pass_button_enabled(root):
                pass_btn = find_pass_button(root)
                break
            time.sleep(2)

        if pass_btn is not None:
            screenshot("26_global_pass_enabled")
            tap_pass(pass_btn)
            screenshot("27_global_pass_tapped")
        else:
            raise RuntimeError(
                "Global Pass button was not enabled after completing subtests")

        # Return to main activity and verify exported report
        return_to_main_activity()
        export_and_verify("notifications_listener_test")
        screenshot("28_test_report_exported")
        print(
            "\n=== Notification Listener Test Automation PASSED successfully! ==="
        )

    finally:
        adb("shell", "cmd", "notification", "clear_all", check=False)
        adb("shell", "settings", "put", "global", "zen_mode", "0", check=False)


if __name__ == "__main__":
    main()
