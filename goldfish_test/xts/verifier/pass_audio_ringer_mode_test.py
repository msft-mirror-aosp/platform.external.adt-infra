#!/usr/bin/env python3
"""Automates CTS Verifier - AUDIO / Ringer Mode Tests."""

import os
import subprocess
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

from cts_common import (
    adb,
    export_and_verify,
    find_node,
    navigate_to,
    set_screenshot_dir,
    setup,
    tap,
    tap_pass,
    ui_dump,
)

TEST_NAME = "Ringer Mode Tests"
set_screenshot_dir("audio_ringer_mode_test")


def get_logcat_lines():
    """Return all InteractiveVerifier lines from logcat."""
    out = subprocess.check_output(
        ["adb", "logcat", "-d", "-s", "InteractiveVerifier:I"],
        stderr=subprocess.DEVNULL,
    ).decode("utf-8", errors="ignore")
    return [line.strip() for line in out.splitlines() if "InteractiveVerifier" in line]


def wait_for_log(substring, count=1, timeout=90):
    """Wait until `substring` appears at least `count` times in InteractiveVerifier logcat."""
    print(f"Waiting for log ({count}x): {substring!r} ...")
    deadline = time.time() + timeout
    last_printed = ""
    while time.time() < deadline:
        lines = get_logcat_lines()
        matches = [l for l in lines if substring in l]
        if len(matches) >= count:
            print(f"  Found ({len(matches)}x): {matches[-1]}")
            return True
        for l in lines:
            if "FAIL:" in l:
                raise RuntimeError(f"Test step failed in InteractiveVerifier: {l}")
        if lines and lines[-1] != last_printed:
            last_printed = lines[-1]
            print(
                f"  [logcat] {last_printed.split('InteractiveVerifier:')[-1].strip()}"
            )
        time.sleep(1.5)
    raise TimeoutError(f"Timed out waiting for {substring!r} (count={count})")


def return_to_verifier():
    """Dismiss any Modes dialog, collapse statusbar, and return to RingerModeActivity."""
    adb("shell", "cmd", "statusbar", "collapse", check=False)
    time.sleep(0.5)
    for _ in range(10):
        root = ui_dump()
        done_btn = find_node(root, text="Done")
        modes_title = find_node(root, resource_id="modes_title")
        if done_btn is not None and modes_title is not None:
            print("  Closing Modes dialog via Done button...")
            tap(done_btn)
            time.sleep(1.0)
            adb("shell", "cmd", "statusbar", "collapse", check=False)
            time.sleep(0.5)
            continue
        pkgs = {
            n.attrib.get("package", "")
            for n in root.iter("node")
            if n.attrib.get("package")
        }
        if "com.android.cts.verifier" in pkgs and "com.android.settings" not in pkgs:
            return
        adb("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
        time.sleep(0.8)


def set_dnd_via_quick_settings(enable, customize_alarms_media_only=False):
    """Open Quick Settings, tap Modes / Do Not Disturb tile, and toggle DND state via UI."""
    print(f"Setting Do Not Disturb via Quick Settings Modes tile: enable={enable}")
    adb("shell", "cmd", "statusbar", "expand-settings")
    time.sleep(1.5)

    root = ui_dump()
    tile = find_node(root, text="Modes")
    if tile is None:
        tile = find_node(root, text="Do Not Disturb")
    if tile is None:
        tile = find_node(root, text_contains="Modes")
    if tile is None:
        tile = find_node(root, text_contains="Do Not Disturb")
    if tile is None:
        adb("shell", "input", "swipe", "540", "300", "540", "1800")
        time.sleep(1.5)
        root = ui_dump()
        tile = find_node(root, text="Modes") or find_node(root, text="Do Not Disturb")
    if tile is None:
        print(
            "  Quick Settings tile not found; using cmd notification set_dnd fallback..."
        )
        adb("shell", "cmd", "statusbar", "collapse", check=False)
        if enable:
            adb("shell", "cmd", "notification", "set_dnd", "priority", check=False)
        else:
            adb("shell", "cmd", "notification", "set_dnd", "off", check=False)
        time.sleep(1.0)
        return_to_verifier()
        return
    tap(tile)
    time.sleep(1.5)

    root = ui_dump()
    nodes = list(root.iter("node"))
    dnd_node = None
    is_on = False
    for i, n in enumerate(nodes):
        if (
            n.attrib.get("text") == "Do Not Disturb"
            and n.attrib.get("resource-id") == "name"
        ):
            dnd_node = n
            if (
                i + 1 < len(nodes)
                and nodes[i + 1].attrib.get("resource-id") == "stateOn"
            ):
                is_on = True
            break

    if dnd_node is None:
        raise RuntimeError("Could not find Do Not Disturb item in Modes dialog")

    if enable and not is_on:
        print("  Tapping Do Not Disturb to turn ON...")
        tap(dnd_node)
        time.sleep(1.0)
    elif not enable and is_on:
        print("  Tapping Do Not Disturb to turn OFF...")
        tap(dnd_node)
        time.sleep(1.0)
    else:
        print(f"  Do Not Disturb already in desired state (is_on={is_on})")

    if customize_alarms_media_only:
        root = ui_dump()
        settings_btn = find_node(root, text="Settings")
        if settings_btn is not None:
            print("  Opening Modes Settings to customize Alarms & Media only...")
            tap(settings_btn)
            time.sleep(1.5)
            root = ui_dump()
            dnd_item = find_node(root, text="Do Not Disturb")
            if dnd_item is not None:
                tap(dnd_item)
                time.sleep(1.5)
                _customize_dnd_alarms_media_only()
            return_to_verifier()
            return

    root = ui_dump()
    done_btn = find_node(root, text="Done")
    if done_btn is not None:
        tap(done_btn)
        time.sleep(1.0)
    return_to_verifier()


def _customize_dnd_alarms_media_only():
    """Ensure People -> None and Apps -> None in Do Not Disturb settings UI."""
    root = ui_dump()
    nodes = list(root.iter("node"))
    people_summary = ""
    apps_summary = ""
    for i, n in enumerate(nodes):
        if n.attrib.get("text") == "People" and i + 1 < len(nodes):
            people_summary = nodes[i + 1].attrib.get("text", "")
        elif n.attrib.get("text") == "Apps" and i + 1 < len(nodes):
            apps_summary = nodes[i + 1].attrib.get("text", "")

    if people_summary != "No one can interrupt":
        people_node = find_node(root, text="People")
        if people_node is not None:
            tap(people_node)
            time.sleep(1.5)
            # Messages -> None
            r = ui_dump()
            msg_node = find_node(r, text="Messages")
            if msg_node is not None:
                tap(msg_node)
                time.sleep(1.5)
                r2 = ui_dump()
                none_node = find_node(r2, text="None")
                if none_node is not None:
                    tap(none_node)
                    time.sleep(1.0)
                adb("shell", "input", "keyevent", "KEYCODE_BACK")
                time.sleep(1.0)
            # Calls -> None and uncheck Allow repeat callers
            r = ui_dump()
            calls_node = find_node(r, text="Calls")
            if calls_node is not None:
                tap(calls_node)
                time.sleep(1.5)
                r2 = ui_dump()
                none_node = find_node(r2, text="None")
                if none_node is not None:
                    tap(none_node)
                    time.sleep(1.0)
                r2 = ui_dump()
                nodes2 = list(r2.iter("node"))
                for idx, n2 in enumerate(nodes2):
                    if n2.attrib.get("text") == "Allow repeat callers":
                        for s in nodes2[idx : idx + 4]:
                            if (
                                s.attrib.get("checkable") == "true"
                                and s.attrib.get("checked") == "true"
                            ):
                                tap(n2)
                                time.sleep(1.0)
                                break
                        break
                adb("shell", "input", "keyevent", "KEYCODE_BACK")
                time.sleep(1.0)
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
            time.sleep(1.5)

    root = ui_dump()
    nodes = list(root.iter("node"))
    for i, n in enumerate(nodes):
        if n.attrib.get("text") == "Apps" and i + 1 < len(nodes):
            apps_summary = nodes[i + 1].attrib.get("text", "")
            break

    if apps_summary != "None":
        apps_node = find_node(root, text="Apps")
        if apps_node is not None:
            tap(apps_node)
            time.sleep(1.5)
            r = ui_dump()
            none_node = find_node(r, text="None")
            if none_node is not None:
                tap(none_node)
                time.sleep(1.0)
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
            time.sleep(1.0)


def set_ringer_mode_normal_via_volume_key():
    """Press volume key and tap the ringer mode icon above the volume slider to set Normal mode."""
    print("Setting ringer mode to Normal via volume key UI...")
    adb("shell", "input", "keyevent", "KEYCODE_VOLUME_UP")
    time.sleep(0.5)
    # Tap ringer mode icon above volume slider
    adb("shell", "input", "tap", "980", "793")
    time.sleep(0.5)
    # Tap Normal mode icon in the expanded selector
    adb("shell", "input", "tap", "980", "800")
    adb("shell", "cmd", "audio", "set-ringer-mode", "NORMAL", check=False)
    time.sleep(3.5)


def enable_sound_effects_via_settings():
    """Open Sound settings via UI, scroll to Tap & click sounds, and ensure switch is ON."""
    print("Enabling Tap & click sounds in Sound settings UI...")
    adb("shell", "am", "start", "-a", "android.settings.SOUND_SETTINGS")
    time.sleep(2.0)
    for _ in range(4):
        root = ui_dump()
        target = find_node(root, text="Tap & click sounds")
        if target is not None:
            nodes = list(root.iter("node"))
            idx = nodes.index(target)
            is_checked = False
            for s in nodes[idx : idx + 4]:
                if s.attrib.get("checkable") == "true":
                    is_checked = s.attrib.get("checked") == "true"
                    break
            if not is_checked:
                print("  Tap & click sounds is OFF, tapping to turn ON...")
                tap(target)
                time.sleep(1.0)
            else:
                print("  Tap & click sounds is already ON")
            break
        adb("shell", "input", "swipe", "540", "1800", "540", "500")
        time.sleep(1.5)
    return_to_verifier()


def tap_current_im_done_button():
    """Tap the first enabled 'I'm done' button (com.android.cts.verifier:id/nls_action_button)."""
    root = ui_dump()
    for n in root.iter("node"):
        if (
            n.attrib.get("resource-id")
            == "com.android.cts.verifier:id/nls_action_button"
            and n.attrib.get("enabled") == "true"
        ):
            print("Tapping current 'I'm done' button...")
            tap(n)
            return
    raise RuntimeError("Could not find an enabled 'I'm done' button in UI")


def main():
    root = ui_dump()
    done_btn = find_node(root, text="Done")
    if done_btn is not None and find_node(root, resource_id="modes_title") is not None:
        tap(done_btn)
        time.sleep(0.5)
    adb("shell", "cmd", "statusbar", "collapse", check=False)
    time.sleep(0.5)
    setup()

    # Ensure CtsVerifier does NOT have notification policy access so TestSetRingerModePolicyAccess* passes
    adb(
        "shell",
        "cmd",
        "notification",
        "disallow_dnd",
        "com.android.cts.verifier",
        check=False,
    )
    adb(
        "shell",
        "cmd",
        "notification",
        "set_notification_listener_access_granted_for_user",
        "com.android.cts.verifier/.notifications.NotificationListenerVerifierActivity$TestListener",
        "0",
        "false",
        check=False,
    )

    # Expand logcat buffer and clear before starting the test
    adb("logcat", "-G", "16M", check=False)
    adb("logcat", "-c", check=False)

    navigate_to(TEST_NAME)
    time.sleep(1.5)
    root = ui_dump()
    ok_btn = find_node(root, text="OK")
    if ok_btn is not None:
        tap(ok_btn)
        time.sleep(1.0)

    # -------------------------------------------------------------------------
    # Step 1: SetModeAllTest #1
    # Instruction: Please disable "Do not disturb" by tapping the Quick Settings tile.
    # -------------------------------------------------------------------------
    wait_for_log("waiting for user: SetModeAllTest", count=1)
    set_dnd_via_quick_settings(enable=False)
    time.sleep(1.0)
    tap_current_im_done_button()
    wait_for_log("pass for: SetModeAllTest", count=1)

    # -------------------------------------------------------------------------
    # Step 2: SetModePriorityTest
    # Instruction: Please enable Priority-Only "Do not disturb" by tapping the Quick Settings tile.
    #              Then, long press the same tile and customize the setting to allow sounds
    #              from Alarms and Media (if applicable) only.
    # -------------------------------------------------------------------------
    wait_for_log("waiting for user: SetModePriorityTest", count=1)
    set_dnd_via_quick_settings(enable=True, customize_alarms_media_only=True)
    time.sleep(1.0)
    tap_current_im_done_button()
    wait_for_log("pass for: SetModePriorityTest", count=1)
    # Wait for all 5 automatic DND sub-tests to complete before Step 3
    wait_for_log(
        "pass for: TestAdjustVolumeInPriorityOnlyAllowAlarmsMediaMode", count=1
    )

    # -------------------------------------------------------------------------
    # Step 3: SetModeAllTest #2
    # Instruction: Please disable "Do not disturb" by tapping the Quick Settings tile.
    # -------------------------------------------------------------------------
    wait_for_log("waiting for user: SetModeAllTest", count=2)
    set_dnd_via_quick_settings(enable=False)
    time.sleep(1.0)
    adb("shell", "input", "swipe", "540", "1600", "540", "800")
    time.sleep(1.0)
    tap_current_im_done_button()
    wait_for_log("pass for: SetModeAllTest", count=2)

    # -------------------------------------------------------------------------
    # Step 4: SetModeNormalTest
    # Instruction: Please set the ringer mode to normal or vibrate by pressing a volume key
    #              and then selecting a mode icon above the volume slider.
    # -------------------------------------------------------------------------
    wait_for_log("waiting for user: SetModeNormalTest", count=1)
    set_ringer_mode_normal_via_volume_key()
    time.sleep(1.0)
    tap_current_im_done_button()
    wait_for_log("pass for: SetModeNormalTest", count=1)
    # Wait for all automatic & async volume tests to complete before Step 5
    wait_for_log("pass for: TestMuteStreams", count=1, timeout=120)

    # -------------------------------------------------------------------------
    # Step 5: EnableSoundEffects
    # Instruction: Please enable Tap & click sounds in Sound settings.
    # -------------------------------------------------------------------------
    wait_for_log("waiting for user: EnableSoundEffects", count=1)
    enable_sound_effects_via_settings()
    time.sleep(1.0)
    adb("shell", "input", "swipe", "540", "1800", "540", "400")
    time.sleep(1.0)
    tap_current_im_done_button()
    wait_for_log("pass for: EnableSoundEffects", count=1)
    wait_for_log("pass for: TestSoundEffects", count=1)
    wait_for_log("no more tests", count=1)

    # Verify Pass button is enabled and tap it
    time.sleep(1.5)
    root = ui_dump()
    pass_btn = find_node(root, resource_id="com.android.cts.verifier:id/pass_button")
    if pass_btn is None or pass_btn.attrib.get("enabled") != "true":
        raise RuntimeError("Pass button is not enabled after completing all steps!")
    print("Tapping Pass button...")
    tap(pass_btn)
    time.sleep(2.0)

    export_and_verify(TEST_NAME)


if __name__ == "__main__":
    main()
