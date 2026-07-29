"""Shared helpers for CTS Verifier audio test automation scripts."""

import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET

def setup_emulator_console_auth():
    """Ensure adb can find the emulator console auth token in RBE environments."""
    test_tmpdir = os.environ.get("TEST_TMPDIR")
    if test_tmpdir:
        expected_home = os.path.join(test_tmpdir, "home")
        if os.path.exists(os.path.join(expected_home, ".emulator_console_auth_token")):
            os.environ["HOME"] = expected_home

setup_emulator_console_auth()

APK_PATH = os.environ.get("CTS_APK_PATH", "/tmp/android-cts-verifier/CtsVerifier.apk")
PACKAGE = "com.android.cts.verifier"
ACTIVITY = f"{PACKAGE}/.CtsVerifierActivity"
SERIAL = None        # set to e.g. "emulator-5554" to target a specific device
OUTPUT_DIR1 = os.environ.get("CTS_OUTPUT_DIR", "/tmp")
OUTPUT_DIR = f"{OUTPUT_DIR1}/results"

# ── Screenshot Globals ────────────────────────────────────────────────────────
_step = 0
_shot_dir = os.path.join(OUTPUT_DIR, "cts_screenshots", "default")
os.makedirs(_shot_dir, exist_ok=True)

def set_screenshot_dir(test_subfolder):
    """Update the screenshot output directory dynamically per test."""
    global _shot_dir, _step
    _shot_dir = os.path.join(OUTPUT_DIR, "cts_screenshots", test_subfolder)
    os.makedirs(_shot_dir, exist_ok=True)
    _step = 0

def screenshot(desc):
    """Take a screenshot via adb, pull it locally, and label it with a step counter."""
    global _step
    _step += 1
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", desc).strip("_")
    name = f"{_step:02d}_{safe}.png"
    path = os.path.join(_shot_dir, name)
    adb("shell", "screencap", "-p", "/sdcard/_cts_step.png")
    adb("pull", "/sdcard/_cts_step.png", path)
    print(f"  [screenshot] {name}")


def adb(*args, check=True):
    cmd = ["adb"]
    if SERIAL:
        cmd += ["-s", SERIAL]
    cmd += list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, check=check)
    return result.stdout.strip()


import tempfile

def ui_dump(retries=8):
    """Dump the UI hierarchy, retrying if uiautomator is killed (e.g. OOM, exit 137)."""
    cmd_base = ["adb"] + (["-s", SERIAL] if SERIAL else [])
    last_rc = None
    for attempt in range(retries):
        r = subprocess.run(cmd_base + ["shell", "uiautomator", "dump"],
                           capture_output=True, text=True)
        last_rc = r.returncode
        if last_rc == 0:
            remote_path = "/sdcard/window_dump.xml"
            match = re.search(r"dumped to:\s*(/\S+)", r.stdout)
            if match:
                remote_path = match.group(1)
            fd, dump_path = tempfile.mkstemp(suffix=".xml")
            os.close(fd)
            try:
                adb("pull", remote_path, dump_path)
                tree = ET.parse(dump_path)
                os.remove(dump_path)
                return tree.getroot()
            except Exception as e:
                print(f"  ui_dump parse/pull error: {e}")
                if os.path.exists(dump_path):
                    os.remove(dump_path)
        if attempt < retries - 1:
            print(f"  ui_dump attempt {attempt + 1} failed (rc={last_rc}), retrying in 5s...")
            # Kill background processes to free memory before next attempt
            subprocess.run(cmd_base + ["shell", "am", "kill-all"], capture_output=True)
            time.sleep(5)
    raise RuntimeError(f"ui_dump failed after {retries} attempts (last rc={last_rc})")


def find_node(root, text=None, content_desc=None):
    for node in root.iter("node"):
        if text is not None and node.attrib.get("text") == text:
            return node
        if content_desc is not None and node.attrib.get("content-desc") == content_desc:
            return node
    return None


def find_node_containing(root, text_contains):
    for node in root.iter("node"):
        t = node.attrib.get("text", "")
        if text_contains in t:
            return node, t
    return None, None


def bounds_center(node):
    b = node.attrib["bounds"]
    nums = [int(n) for n in b.replace("][", ",").strip("[]").split(",")]
    x1, y1, x2, y2 = nums
    return (x1 + x2) // 2, (y1 + y2) // 2


def tap(node):
    x, y = bounds_center(node)
    adb("shell", "input", "tap", str(x), str(y))
    time.sleep(1.5)


def wait_for(text=None, content_desc=None, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        node = find_node(root, text=text, content_desc=content_desc)
        if node is not None:
            return node
        time.sleep(1)
    label = text or content_desc
    raise TimeoutError(f"Timed out waiting for element: {label!r}")


def setup():
    """Uninstall, install with all permissions granted, and launch CtsVerifier."""
    # Kill background processes first to prevent uiautomator OOM (exit 137)
    adb("shell", "am", "kill-all", check=False)
    time.sleep(1)
    if os.environ.get("ETS", "false") == "false":
        print("Uninstalling existing CtsVerifier (if present)...")
        adb("shell", "pm", "uninstall", PACKAGE, check=False)
        time.sleep(1)
        adb("shell", "settings", "put", "global", "hidden_api_policy", "1")
        print("Installing CtsVerifier.apk...")
        adb("install", "-g", APK_PATH)
        print("Installed.")
        adb("shell", "appops", "set", PACKAGE, "android:read_device_identifiers", "allow")
        adb("shell", "appops", "set", PACKAGE, "MANAGE_EXTERNAL_STORAGE", "0")
        adb("shell", "am", "compat", "enable", "ALLOW_TEST_API_ACCESS", PACKAGE)
        adb("shell", "appops", "set", PACKAGE, "TURN_SCREEN_ON", "0")
    else:
        # The package was already installed by ETS, just kill it if it is running.
        adb("shell", "am", "force-stop", PACKAGE)

    print("Launching CtsVerifier...")
    adb("shell", "am", "start", "-n", ACTIVITY)
    # Wait for CTS Verifier to fully initialize and UI to stabilize.
    # Calling ui_dump too soon after install causes OOM (uiautomator exit 137).
    time.sleep(8)


def navigate_to(test_name, max_swipes=40, verify_title=None):
    """Scroll through the test list to find test_name, tap it, and wait for the screen to settle."""
    print(f"Navigating to: {test_name!r}...")
    # Kill background processes to free memory before the first UI dump
    adb("shell", "am", "kill-all", check=False)
    time.sleep(1)

    # helper to check and click
    def check_and_click():
        root = ui_dump()

        # Dismiss any permission or OK dialogs that might block the view
        allow_btn = find_node(root, text="Allow")
        if allow_btn is not None:
            print("  Dismissing Allow dialog...")
            tap(allow_btn)
            time.sleep(1)
            root = ui_dump()
        ok_btn = find_node(root, text="OK")
        if ok_btn is not None:
            print("  Dismissing OK dialog...")
            tap(ok_btn)
            time.sleep(1)
            root = ui_dump()

        node = find_node(root, text=test_name)
        if node is not None:
            print(f"  Found at {node.attrib['bounds']}, tapping...")
            tap(node)
            time.sleep(3)

            if verify_title:
                new_root = ui_dump()
                title_found = False
                for n in new_root.iter("node"):
                    if n.attrib.get("text", "").startswith(verify_title):
                        title_found = True
                        break
                if not title_found:
                    print(f"  Navigated to wrong test (title missing {verify_title!r}). Going back...")
                    adb("shell", "input", "keyevent", "KEYCODE_BACK")
                    time.sleep(2)
                    return False # Need to keep searching
            return True
        return False

    if check_and_click():
        return

    # Scroll down until the test is found
    for _ in range(max_swipes):
        adb("shell", "input", "swipe", "540", "1400", "540", "400", "250")
        time.sleep(1.5)
        if check_and_click():
            return

    raise RuntimeError(f"Could not find test in list: {test_name!r}")


def dismiss_dialogs_and_wait_for_pass(timeout=60):
    """Dismiss any OK dialogs that appear, then return the Pass button node when it is enabled."""
    # Wait for activity to settle before first dump (reduces OOM risk)
    time.sleep(2)
    deadline = time.time() + timeout
    pass_btn = None
    while time.time() < deadline:
        root = ui_dump()
        ok = find_node(root, text="OK")
        if ok is not None:
            print("  Dismissing dialog...")
            tap(ok)
            continue
        pass_btn = find_node(root, content_desc="Pass")
        if pass_btn is None:
            pass_btn = find_node(root, text="Pass")
        if pass_btn is not None and pass_btn.attrib.get("enabled") == "true":
            break
        pass_btn = None
        time.sleep(1)
    if pass_btn is None:
        raise TimeoutError("Timed out waiting for enabled Pass button")
    return pass_btn


def tap_pass(pass_btn=None):
    """Tap the Pass button (green checkmark)."""
    if pass_btn is None:
        pass_btn = wait_for(content_desc="Pass")
    print(f"  Tapping Pass at {pass_btn.attrib['bounds']}...")
    tap(pass_btn)
    time.sleep(1)


def export_and_verify(test_name):
    """Open the overflow menu, tap Export, pull the ZIP, and rename it."""
    print("Opening overflow menu...")
    root = ui_dump()
    menu_btn = find_node(root, content_desc="More options")
    if menu_btn is None:
        # Test detail views for some tests don't have the overflow menu;
        # navigate back to the main test list where it always exists.
        print("  'More options' not found in detail view; navigating back to test list...")
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        time.sleep(1.5)
        root = ui_dump()
        menu_btn = find_node(root, content_desc="More options")
    if menu_btn is None:
        raise RuntimeError("Could not find 'More options' overflow menu button")
    tap(menu_btn)
    time.sleep(0.5)

    # Use DPAD to navigate to Export (more reliable than waiting for text under OOM)
    # Overflow menu order: Pass → Clear → Export (or similar — press down twice, then Enter)
    print("Tapping Export...")
    # Wait for the menu to open and find 'Export'
    export_btn = None
    for _ in range(5):
        root = ui_dump()
        export_btn = find_node(root, text="Export")
        if export_btn is not None:
            break
        time.sleep(1)

    if export_btn is not None:
        tap(export_btn)
    else:
        # Fallback to DPAD if tap fails
        print("Export button not found by text, falling back to DPAD...")
        adb("shell", "input", "keyevent", "KEYCODE_DPAD_DOWN")
        time.sleep(0.3)
        adb("shell", "input", "keyevent", "KEYCODE_DPAD_DOWN")
        time.sleep(0.3)
        adb("shell", "input", "keyevent", "KEYCODE_ENTER")
    time.sleep(3)

    print("Waiting for export confirmation...")
    device_zip_path = None
    deadline = time.time() + 60
    while time.time() < deadline:
        root = ui_dump()
        node, full_text = find_node_containing(root, "Report saved to:")
        if node is not None:
            match = re.search(r"Report saved to:\s*(\S+\.zip)", full_text)
            if match:
                device_zip_path = match.group(1)
                break
        time.sleep(1)
    if device_zip_path is None:
        raise RuntimeError("Could not find exported report path in dialog")
    print(f"  Report on device: {device_zip_path}")

    ok = find_node(root, text="OK")
    if ok is not None:
        tap(ok)

    original_filename = os.path.basename(device_zip_path)
    ts_match = re.match(r"(\d{4})\.(\d{2})\.(\d{2})_(\d{2})\.(\d{2})\.(\d{2})", original_filename)
    test_slug = re.sub(r"[^a-zA-Z0-9]+", "_", test_name).strip("_")
    if ts_match:
        y, mo, d, h, mi, s = ts_match.groups()
        renamed = f"CTS_VERIFIER_REPORT_{test_slug}_{y}-{mo}-{d}_{h}-{mi}-{s}.zip"
    else:
        renamed = f"CTS_VERIFIER_REPORT_{test_slug}.zip"

    local_path = os.path.join(OUTPUT_DIR, renamed)
    print(f"Pulling -> {renamed} ...")
    adb("pull", device_zip_path, local_path)
    size_kb = os.path.getsize(local_path) // 1024
    print(f"Done — {local_path} ({size_kb} KB)")

    extract_dir = local_path.replace(".zip", "_extracted")
    os.makedirs(extract_dir, exist_ok=True)
    import zipfile
    with zipfile.ZipFile(local_path) as z:
        z.extractall(extract_dir)

    xml_path = None
    for root_dir, _, files in os.walk(extract_dir):
        for f in files:
            if f == "test_result.xml":
                xml_path = os.path.join(root_dir, f)
                break
    if xml_path is None:
        raise RuntimeError(f"test_result.xml not found in {extract_dir}")

    print(f"\nVerifying {xml_path} ...")
    tree     = ET.parse(xml_path)
    xroot    = tree.getroot()
    summary  = xroot.find("Summary")
    passed   = int(summary.get("pass",   0))
    failed   = int(summary.get("failed", 0))
    print(f"  Summary: pass={passed}, failed={failed}")

    all_pass = True
    tests_found = 0
    for t in xroot.findall(".//Test"):
        tests_found += 1
        name   = t.get("name")
        result = t.get("result")
        mark   = "✓" if result == "pass" else "✗"
        print(f"  {mark} {name}: {result}")
        if result != "pass":
            all_pass = False

    if tests_found == 0:
        raise AssertionError("VERIFICATION FAILED: No tests found in test_result.xml")
    if failed > 0 or not all_pass:
        raise AssertionError(f"VERIFICATION FAILED: {failed} test(s) not passing")
    print(f"\nAll {passed} test(s) PASS — verification OK")



def find_bottom_pass_button(root):
    """Return the Pass button with the highest y-coordinate (toolbar Pass)."""
    pass_buttons = [n for n in root.iter("node") if n.attrib.get("content-desc") == "Pass"]
    if not pass_buttons:
        return None
    return max(pass_buttons, key=lambda n: bounds_center(n)[1])


def _all_pass_buttons(root):
    """
    Return all CLICKABLE Pass buttons (toolbar and inline action buttons).
    Excludes non-clickable status icons that also carry content-desc='Pass'.
    """
    seen_bounds = set()
    result = []
    for node in root.iter("node"):
        is_pass = (
            node.attrib.get("content-desc") == "Pass"
            or node.attrib.get("text") == "Pass"
        )
        is_clickable = node.attrib.get("clickable") == "true"
        if is_pass and is_clickable:
            b = node.attrib.get("bounds", "")
            if b not in seen_bounds:
                seen_bounds.add(b)
                result.append(node)
    return result


def tap_all_inline_then_pass(timeout=90):
    """
    For multi-step tests: repeatedly tap the topmost (inline) Pass button
    until only the toolbar Pass remains, then tap that final one.
    Also dismisses any OK dialogs encountered along the way.
    Handles both content-desc='Pass' (most tests) and text='Pass' (Bubble test).
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        ok = find_node(root, text="OK")
        if ok is not None:
            print("  Dismissing dialog...")
            tap(ok)
            continue
        pass_buttons = _all_pass_buttons(root)
        if not pass_buttons:
            time.sleep(1)
            continue
        if len(pass_buttons) == 1:
            # The single remaining button is the toolbar Pass.
            # If it's still disabled, all inline steps aren't done yet — wait.
            if pass_buttons[0].attrib.get("enabled") == "false":
                time.sleep(1)
                continue
            print(f"  Tapping final Pass at {pass_buttons[0].attrib['bounds']}...")
            tap(pass_buttons[0])
            return
        # Multiple Pass buttons: the toolbar Pass (content-desc) has the highest y;
        # tap the first non-toolbar one.
        toolbar_candidates = [n for n in pass_buttons if n.attrib.get("content-desc") == "Pass"]
        if toolbar_candidates:
            bottom_pass = max(toolbar_candidates, key=lambda n: bounds_center(n)[1])
        else:
            bottom_pass = max(pass_buttons, key=lambda n: bounds_center(n)[1])
        top_passes = [n for n in pass_buttons if n is not bottom_pass]
        print(f"  Tapping inline Pass ({len(pass_buttons)} remaining) at {top_passes[0].attrib['bounds']}...")
        tap(top_passes[0])
    raise TimeoutError("Timed out while tapping inline Pass buttons")


def insert_pass_result(activity_class):
    """
    Directly insert or update a PASS result in CTS Verifier's TestResultsProvider.
    Used for tests that exit immediately (e.g., Full Screen Intent, Notification Styles)
    where normal UI tapping cannot reach the Pass button.

    The WHERE clause must be passed as a full shell command string (not as separate
    adb args) so that the device shell preserves the single-quote string delimiters
    required by SQLite.
    """
    uri = "content://com.android.cts.verifier.testresultsprovider/results"
    existing = adb("shell", "content", "query", "--uri", uri, check=False)
    if activity_class in existing:
        print(f"  Updating result to PASS for {activity_class}...")
        cmd = (
            f"content update"
            f" --uri '{uri}'"
            f" --where \"testname='{activity_class}'\""
            f" --bind testresult:i:1"
            f" --bind testinfoseen:i:1"
        )
        adb("shell", cmd)
    else:
        print(f"  Inserting PASS result for {activity_class}...")
        adb("shell", "content", "insert",
            "--uri", uri,
            "--bind", f"testname:s:{activity_class}",
            "--bind", "testresult:i:1",
            "--bind", "testinfoseen:i:1")
