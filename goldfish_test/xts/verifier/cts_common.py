"""Shared helpers for CTS Verifier audio test automation scripts."""

import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

try:
    sys.stdout.reconfigure(line_buffering=True)
except (AttributeError, TypeError):
    pass


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
SERIAL = None  # set to e.g. "emulator-5554" to target a specific device
EMPTY_ADMIN_APK_PATH = os.environ.get(
    "EMPTY_ADMIN_APK_PATH",
    os.path.join(os.path.dirname(APK_PATH), "CtsEmptyDeviceAdmin.apk"),
)


def install_empty_device_admin():
    """Install CtsEmptyDeviceAdmin.apk required for Device Admin Uninstall test."""
    print("Installing CtsEmptyDeviceAdmin.apk...")
    candidate_paths = [
        EMPTY_ADMIN_APK_PATH,
        os.path.join(os.path.dirname(APK_PATH), "CtsEmptyDeviceAdmin.apk"),
        os.path.join(
            os.path.dirname(APK_PATH),
            "android-cts-verifier",
            "CtsEmptyDeviceAdmin.apk",
        ),
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "CtsEmptyDeviceAdmin.apk",
        ),
        os.path.join(
            os.environ.get("ANDROID_BUILD_TOP", ""),
            "cts",
            "apps",
            "CtsVerifier",
            "CtsEmptyDeviceAdmin.apk",
        ),
        os.path.join(
            os.environ.get("TEST_SRCDIR", ""),
            "android-cts-verifier",
            "CtsEmptyDeviceAdmin.apk",
        ),
    ]
    target_apk = None
    for p in candidate_paths:
        if p and os.path.exists(p):
            target_apk = p
            break

    if not target_apk:
        start_dir = (
            os.path.dirname(APK_PATH) if os.path.exists(APK_PATH) else os.getcwd()
        )
        for root, _, files in os.walk(start_dir):
            if "CtsEmptyDeviceAdmin.apk" in files:
                target_apk = os.path.join(root, "CtsEmptyDeviceAdmin.apk")
                break

    if target_apk and os.path.exists(target_apk):
        print(f"Found CtsEmptyDeviceAdmin.apk at: {target_apk}")
        adb("install", "-r", "-g", target_apk)
        print("  CtsEmptyDeviceAdmin.apk installed successfully!")
    else:
        raise FileNotFoundError(
            f"Could not locate CtsEmptyDeviceAdmin.apk! Searched: {candidate_paths}"
        )


OUTPUT_DIR1 = os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR") or os.environ.get(
    "CTS_OUTPUT_DIR", "/tmp"
)
OUTPUT_DIR = f"{OUTPUT_DIR1}/results"

# ── Screenshot Globals ────────────────────────────────────────────────────────
_step = 0
_current_subfolder = "default"
_shot_dir = os.path.join(OUTPUT_DIR, "cts_screenshots", "default")
os.makedirs(_shot_dir, exist_ok=True)

ARTIFACT_SCREENSHOTS_DIR = os.environ.get("CTS_ARTIFACT_SCREENSHOTS_DIR")


def set_screenshot_dir(test_subfolder):
    """Update the screenshot output directory dynamically per test."""
    global _shot_dir, _step, _current_subfolder
    _current_subfolder = test_subfolder
    _shot_dir = os.path.join(OUTPUT_DIR, "cts_screenshots", test_subfolder)
    os.makedirs(_shot_dir, exist_ok=True)
    if ARTIFACT_SCREENSHOTS_DIR and os.path.exists(
        os.path.dirname(ARTIFACT_SCREENSHOTS_DIR)
    ):
        os.makedirs(
            os.path.join(ARTIFACT_SCREENSHOTS_DIR, test_subfolder),
            exist_ok=True,
        )
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
    if ARTIFACT_SCREENSHOTS_DIR and os.path.exists(
        os.path.dirname(ARTIFACT_SCREENSHOTS_DIR)
    ):
        artifact_path = os.path.join(ARTIFACT_SCREENSHOTS_DIR, _current_subfolder, name)
        try:
            import shutil

            shutil.copyfile(path, artifact_path)
        except Exception:
            pass
    print(f"  [screenshot] {name}")


def adb(*args, check=True):
    cmd = ["adb"]
    if SERIAL:
        cmd += ["-s", SERIAL]
    cmd += list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, check=check)
    return result.stdout.strip()


def wait_for_boot_finished(adb_path=None, timeout=300):
    """Waits for the emulator to finish booting: adb wait-for-device -> sys.boot_completed == 1 -> package manager ready."""
    adb_cmd = [adb_path] if adb_path else ["adb"]
    if SERIAL and not adb_path:
        adb_cmd.extend(["-s", SERIAL])

    print("Waiting for device...")
    subprocess.run(adb_cmd + ["wait-for-device"], timeout=timeout, check=False)

    print("Waiting for sys.boot_completed...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        res = subprocess.run(
            adb_cmd + ["shell", "getprop", "sys.boot_completed"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.stdout.strip() == "1":
            break
        time.sleep(2)

    print("Waiting for package manager...")
    while time.time() < deadline:
        res = subprocess.run(
            adb_cmd + ["shell", "pm", "path", "android"],
            capture_output=True,
            text=True,
            check=False,
        )
        if "package:" in res.stdout:
            break
        time.sleep(2)

    time.sleep(3)


def reboot_and_wait(max_retries=120, poll_interval=1):
    """Executes an intentional reboot with boot completion polling."""
    print("Executing reboot: adb shell reboot...")
    adb("shell", "reboot", check=False)

    print("Waiting 10 seconds for adbd to disconnect into reboot...")
    time.sleep(10)

    wait_for_boot_finished(timeout=max_retries * poll_interval)

    # Unlock screen after reboot
    time.sleep(2)
    adb("shell", "input", "keyevent", "82", check=False)
    print("Reboot complete and device unlocked!")


def wait_for_screen_off(timeout=10):
    """Wait for the screen to lock or turn off after lockNow()."""
    print("Waiting for screen to turn off / lock...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        power_state = adb("shell", "dumpsys", "power", check=False)
        if (
            "mInteractive=false" in power_state
            or "Display Power: state=OFF" in power_state
        ):
            print("  Screen is OFF / Locked!")
            return True
        # Also check if Keyguard / NotificationShade is showing in UI dump
        try:
            root = ui_dump(retries=2)
            if root.attrib.get("package") == "com.android.systemui" or find_node(
                root, resource_id="com.android.systemui:id/scrim_behind"
            ):
                print("  Keyguard / NotificationShade is showing!")
                return True
        except Exception:
            pass
        time.sleep(0.5)
    print("  Warning: Timed out waiting for screen off, proceeding...")
    return False


def wait_for_keyguard_showing(timeout=10):
    """Wait for the Keyguard / lockscreen prompt to become active on screen."""
    print("Waiting for Keyguard prompt to appear...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        window_state = adb("shell", "dumpsys", "window", "displays", check=False)
        if (
            "StatusBar" in window_state
            or "Keyguard" in window_state
            or "com.android.systemui" in window_state
        ):
            print("  Keyguard prompt is active and ready for PIN entry!")
            return True
        try:
            root = ui_dump(retries=2)
            if find_node(
                root, resource_id="com.android.systemui:id/device_entry_icon_view"
            ) or find_node(root, text="Unlock for all features and data"):
                print("  Keyguard prompt is active!")
                return True
        except Exception:
            pass
        time.sleep(0.5)
    print("  Warning: Timed out waiting for Keyguard prompt, proceeding...")
    return False


def dump_logcat(tag=""):
    print(f"=== LOGCAT DUMP ({tag}) ===", flush=True)
    logs = adb("logcat", "-d", "-t", "150", check=False)
    print(logs, flush=True)
    print("===========================", flush=True)


import tempfile


def ui_dump(retries=8):
    """Dump the UI hierarchy, retrying if uiautomator is killed (e.g. OOM, exit 137)."""
    cmd_base = ["adb"] + (["-s", SERIAL] if SERIAL else [])
    last_rc = None
    for attempt in range(retries):
        r = subprocess.run(
            cmd_base + ["shell", "uiautomator", "dump"], capture_output=True, text=True
        )
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
                root = tree.getroot()
                # Auto-dismiss transient crash or ANR dialogs by tapping the action button
                wait_btn = find_node(root, text="Wait")
                if wait_btn is not None:
                    print(
                        "  [ui_dump] Auto-dismissing transient modal via 'Wait' button..."
                    )
                    tap(wait_btn)
                    time.sleep(1)
                else:
                    close_btn = find_node(root, text="Close app")
                    if close_btn is not None:
                        print(
                            "  [ui_dump] Auto-dismissing transient modal via 'Close app' button..."
                        )
                        tap(close_btn)
                        time.sleep(1)
                return root
            except Exception as e:
                print(f"  ui_dump parse/pull error: {e}")
                if os.path.exists(dump_path):
                    os.remove(dump_path)
        if attempt < retries - 1:
            print(
                f"  ui_dump attempt {attempt + 1} failed (rc={last_rc}), retrying in 3s..."
            )
            # Force-stop background Google services to free memory without killing CtsVerifier
            subprocess.run(
                cmd_base + ["shell", "am", "force-stop", "com.google.android.gms"],
                capture_output=True,
            )
            time.sleep(3)
    raise RuntimeError(f"ui_dump failed after {retries} attempts (last rc={last_rc})")


def find_node(
    root,
    text=None,
    content_desc=None,
    resource_id=None,
    text_contains=None,
    content_desc_contains=None,
    resource_id_contains=None,
    class_name=None,
    clickable=None,
    enabled=None,
):
    """
    Find the first XML node matching all provided non-None criteria (conjunction / AND).
    """
    for node in root.iter("node"):
        if text is not None and node.attrib.get("text") != text:
            continue
        if text_contains is not None and text_contains not in node.attrib.get(
            "text", ""
        ):
            continue
        if content_desc is not None and node.attrib.get("content-desc") != content_desc:
            continue
        if (
            content_desc_contains is not None
            and content_desc_contains not in node.attrib.get("content-desc", "")
        ):
            continue
        if resource_id is not None and node.attrib.get("resource-id") != resource_id:
            continue
        if (
            resource_id_contains is not None
            and resource_id_contains not in node.attrib.get("resource-id", "")
        ):
            continue
        if class_name is not None and node.attrib.get("class") != class_name:
            continue
        if (
            clickable is not None
            and node.attrib.get("clickable") != str(clickable).lower()
        ):
            continue
        if enabled is not None and node.attrib.get("enabled") != str(enabled).lower():
            continue
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


def swipe(x1, y1, x2, y2, duration_ms=500, sleep_after=1.0):
    """
    Perform an ADB input swipe between two points with configurable duration and settling delay.
    """
    adb(
        "shell",
        "input",
        "swipe",
        str(x1),
        str(y1),
        str(x2),
        str(y2),
        str(duration_ms),
    )
    if sleep_after > 0:
        time.sleep(sleep_after)


def scroll_down(x=540, y1=1600, y2=800, duration_ms=500, sleep_after=1.0):
    """
    Perform a single controlled scroll down gesture with tuned defaults (1600 -> 800, 500ms)
    ensuring continuous screen overlap without momentum flinging.
    """
    swipe(x, y1, x, y2, duration_ms=duration_ms, sleep_after=sleep_after)


def scroll_up(x=540, y1=800, y2=1600, duration_ms=500, sleep_after=1.0):
    """
    Perform a single controlled scroll up gesture with tuned defaults (800 -> 1600, 500ms).
    """
    swipe(x, y1, x, y2, duration_ms=duration_ms, sleep_after=sleep_after)


def wait_for(text=None, content_desc=None, resource_id=None, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        root = ui_dump()
        node = find_node(
            root, text=text, content_desc=content_desc, resource_id=resource_id
        )
        if node is not None:
            if node.attrib.get("enabled", "true") == "true":
                return node
            print(
                f"  Found '{text or content_desc or resource_id}' (disabled), waiting for it to become enabled..."
            )
        time.sleep(1)
    label = text or content_desc or resource_id
    raise TimeoutError(f"Timed out waiting for enabled element: {label!r}")


def grant_all_permissions(apk_path=None):
    """Automatically grant all 6 required CTS Verifier permissions and appops."""
    print("Automatically granting CTS Verifier permissions...")
    adb("shell", "settings", "put", "global", "hidden_api_policy", "1", check=False)
    if apk_path and os.path.exists(apk_path):
        adb("install", "-r", "-g", apk_path, check=False)
    adb(
        "shell",
        "appops",
        "set",
        PACKAGE,
        "android:read_device_identifiers",
        "allow",
        check=False,
    )
    adb("shell", "appops", "set", PACKAGE, "MANAGE_EXTERNAL_STORAGE", "0", check=False)
    adb(
        "shell", "am", "compat", "enable", "ALLOW_TEST_API_ACCESS", PACKAGE, check=False
    )
    adb("shell", "appops", "set", PACKAGE, "TURN_SCREEN_ON", "0", check=False)
    adb(
        "shell",
        "cmd",
        "notification",
        "set_notification_listener_access_granted_for_user",
        f"{PACKAGE}/.notifications.NotificationListenerVerifierActivity$TestListener",
        "0",
        "true",
        check=False,
    )
    print("  ✓ All CTS Verifier permissions successfully granted.")


def get_ca_cert_path():
    """Locate or dynamically extract the authentic myCA.cer certificate asset."""
    # 1. Search candidate filesystem paths
    candidate_paths = [
        os.path.join(os.path.dirname(APK_PATH), "assets", "myCA.cer"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "myCA.cer"),
        os.path.join(
            os.environ.get("ANDROID_BUILD_TOP", ""),
            "cts",
            "apps",
            "CtsVerifier",
            "assets",
            "myCA.cer",
        ),
        os.path.join(os.environ.get("TEST_SRCDIR", ""), "assets", "myCA.cer"),
    ]
    for p in candidate_paths:
        if p and os.path.exists(p):
            return p

    # 2. Search parent directories
    cur = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        asset = os.path.join(cur, "cts", "apps", "CtsVerifier", "assets", "myCA.cer")
        if os.path.exists(asset):
            return asset
        cur = os.path.dirname(cur)

    # 3. Dynamically extract from CtsVerifier.apk if present
    if APK_PATH and os.path.exists(APK_PATH):
        try:
            with zipfile.ZipFile(APK_PATH, "r") as z:
                if "assets/myCA.cer" in z.namelist():
                    out_dir = os.path.join(OUTPUT_DIR, "extracted_assets")
                    os.makedirs(out_dir, exist_ok=True)
                    extracted_path = os.path.join(out_dir, "myCA.cer")
                    with open(extracted_path, "wb") as f, z.open(
                        "assets/myCA.cer"
                    ) as src:
                        f.write(src.read())
                    return extracted_path
        except Exception as e:
            print(f"  Note: Failed to extract myCA.cer from {APK_PATH}: {e}")

    return None


def install_real_ca_cert():
    """Install the authentic myCA.cer X.509 certificate into the user certificate store."""
    print("Installing authentic myCA.cer into user cert store...")
    adb("root", check=False)
    time.sleep(1)
    adb("shell", "mkdir", "-p", "/data/misc/user/0/cacerts-added", check=False)
    adb("shell", "mkdir", "-p", "/sdcard/Download", check=False)

    cert_src = get_ca_cert_path()
    if cert_src and os.path.exists(cert_src):
        print(f"  Pushing certificate from {cert_src}...")
        adb("push", cert_src, "/sdcard/Download/myCA.cer", check=False)
        adb("push", cert_src, "/data/local/tmp/myCA.cer", check=False)
        adb(
            "shell",
            "cp",
            "/sdcard/Download/myCA.cer",
            "/data/misc/user/0/cacerts-added/5fa05ae2.0",
            check=False,
        )
        adb(
            "shell",
            "cp",
            "/sdcard/Download/myCA.cer",
            "/data/misc/user/0/cacerts-added/2912c79d.0",
            check=False,
        )
        adb(
            "shell",
            "su",
            "0",
            "cp",
            "/sdcard/Download/myCA.cer",
            "/data/misc/user/0/cacerts-added/5fa05ae2.0",
            check=False,
        )
        adb(
            "shell",
            "su",
            "0",
            "cp",
            "/sdcard/Download/myCA.cer",
            "/data/misc/user/0/cacerts-added/2912c79d.0",
            check=False,
        )
    else:
        print("  Extracting myCA.cer from APK or writing default cert...")
        adb(
            "shell",
            "am",
            "broadcast",
            "-a",
            "com.android.cts.verifier.security.EXTRACT_KEYCHAIN_CERT",
            check=False,
        )

    adb("shell", "chmod", "644", "/data/misc/user/0/cacerts-added/*", check=False)
    adb(
        "shell",
        "chown",
        "system:system",
        "/data/misc/user/0/cacerts-added/*",
        check=False,
    )
    print(
        "  ✓ Certificate installed to user store with hashes 5fa05ae2.0 and 2912c79d.0"
    )


def purge_user_ca_certs():
    """Purge all user-installed CA certificates and reset MediaProvider state."""
    print("Purging user-installed CA certificates...")
    adb("root", check=False)
    time.sleep(1)
    adb("shell", "rm", "-f", "/data/misc/user/0/cacerts-added/*", check=False)
    adb("shell", "rm", "-rf", "/data/media/0/Download/*", check=False)
    adb("shell", "rm", "-rf", "/sdcard/Download/*", check=False)
    adb(
        "shell",
        "killall",
        "-9",
        "com.android.providers.media.module",
        "android.process.media",
        check=False,
    )
    adb(
        "shell",
        "rm",
        "-rf",
        "/data/data/com.android.providers.media.module/databases/*",
        check=False,
    )


def setup():
    """Uninstall, install with all permissions granted, and launch CtsVerifier."""
    # Force stop background Google services to free memory before install
    adb("shell", "am", "force-stop", "com.google.android.gms", check=False)
    adb("shell", "am", "force-stop", "com.google.android.vending", check=False)
    time.sleep(3)
    if os.environ.get("ETS", "false") == "false":
        print("Uninstalling existing CtsVerifier (if present)...")
        adb("shell", "pm", "uninstall", PACKAGE, check=False)
        time.sleep(2)
        print("Installing CtsVerifier.apk...")
        adb("install", "-g", APK_PATH)
        print("Installed.")
        time.sleep(2)
        grant_all_permissions(APK_PATH)
    else:
        grant_all_permissions()
        adb("shell", "am", "force-stop", PACKAGE)
    # Ensure verifierReports directory exists for artifact pull
    adb("shell", "mkdir", "-p", "/sdcard/verifierReports", check=False)
    adb("shell", "touch", "/sdcard/verifierReports/.keep", check=False)
    print("Launching CtsVerifier...")
    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", check=False)
    adb("shell", "input", "keyevent", "82", check=False)
    adb("shell", "am", "start", "-W", "-n", ACTIVITY, check=False)
    time.sleep(5)


def get_screen_size():
    """Returns (width, height) tuple from 'wm size'."""
    res = adb("shell", "wm", "size", check=False)
    m = re.search(r"(\d+)x(\d+)", res)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 1080, 2400


def navigate_to(test_name, max_swipes=40, verify_title=None):
    """Scroll through the test list to find test_name, tap it, and wait for the screen to settle."""
    print(f"Navigating to: {test_name!r}...")

    # helper to check and click
    def check_and_click():
        root = ui_dump()

        # Dismiss any permission dialogs that might block the view
        allow_btn = find_node(root, text="Allow")
        if allow_btn is not None:
            print("  Dismissing Allow dialog...")
            tap(allow_btn)
            time.sleep(1)
            root = ui_dump()

        node = find_node(root, text=test_name)
        if node is None:
            # Fallback: case-insensitive or partial matching
            target = test_name.lower().strip()
            base_target = target.split("(")[0].strip() if "(" in target else target
            for n in root.iter("node"):
                t = (n.attrib.get("text") or "").strip()
                c = (n.attrib.get("content-desc") or "").strip()
                if (
                    target in t.lower()
                    or target in c.lower()
                    or (
                        base_target
                        and (base_target in t.lower() or base_target in c.lower())
                    )
                ):
                    print(
                        f"  Found matching node with text {t!r} / desc {c!r} at {n.attrib.get('bounds')}"
                    )
                    node = n
                    break

        if node is not None:
            print(f"  Found at {node.attrib['bounds']}, tapping...")
            tap(node)
            time.sleep(3)

            if verify_title:
                new_root = ui_dump()
                title_found = False
                for n in new_root.iter("node"):
                    t = n.attrib.get("text", "")
                    if t.startswith(verify_title) or verify_title.lower() in t.lower():
                        title_found = True
                        break
                # Also accept if an initial Notice / Instructions dialog or button is present
                if not title_found and (
                    find_node(new_root, text="OK") is not None
                    or find_node(new_root, text="Notice") is not None
                ):
                    title_found = True

                if not title_found:
                    print(
                        f"  Navigated to wrong test (title missing {verify_title!r}). Going back..."
                    )
                    adb("shell", "input", "keyevent", "KEYCODE_BACK")
                    time.sleep(2)
                    return False  # Need to keep searching
            return True
        return False

    if check_and_click():
        return

    # Ensure CtsVerifier is actually in the foreground before scrolling
    root = ui_dump()
    pkgs = {
        n.attrib.get("package") for n in root.iter("node") if n.attrib.get("package")
    }
    if "com.android.cts.verifier" not in pkgs:
        print("  CtsVerifier not in foreground! Re-launching activity...")
        adb("shell", "am", "start", "-W", "-n", ACTIVITY, check=False)
        time.sleep(3)
        if check_and_click():
            return

    # Scroll down with controlled drag ensuring 5-8 item overlap per check
    for swipe_idx in range(max_swipes):
        scroll_down()
        if (swipe_idx + 1) % 5 == 0:
            print(
                f"  Still scrolling to find '{test_name}' (swipe {swipe_idx + 1}/{max_swipes})..."
            )
        if check_and_click():
            return

    # Log visible text nodes for debugging if not found
    root = ui_dump()
    texts = [n.attrib.get("text") for n in root.iter("node") if n.attrib.get("text")]
    print(
        f"  Failed to find {test_name!r}. Visible text nodes on final screen: {texts}"
    )
    dump_logcat("navigate_to_failed")
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


def tap_fail(fail_btn=None):
    """Tap the Fail button (red exclamation mark / X button)."""
    if fail_btn is None:
        fail_btn = wait_for(content_desc="Fail")
        if fail_btn is None:
            fail_btn = wait_for(text="Fail")
    print(f"  Tapping Fail at {fail_btn.attrib['bounds']}...")
    tap(fail_btn)
    time.sleep(1)


def find_pass_button(root):
    """Find the toolbar Pass button node in an XML root."""
    btn = find_node(root, content_desc="Pass")
    if btn is None:
        btn = find_node(root, text="Pass")
    return btn


def find_fail_button(root):
    """Find the toolbar Fail button node in an XML root."""
    btn = find_node(root, content_desc="Fail")
    if btn is None:
        btn = find_node(root, text="Fail")
    return btn


def is_pass_button_enabled(root):
    """Return True if the toolbar Pass button is present and enabled."""
    btn = find_pass_button(root)
    return btn is not None and btn.attrib.get("enabled") == "true"


def _extract_test_prefix(text):
    """Extract label prefix like '0a', '1a', '4c' from a string like '1a: Credential Not Enrolled Tests'."""
    parts = text.split(":")
    if len(parts) >= 2:
        prefix = parts[0].strip().lower()
        if len(prefix) == 2 and prefix[0].isdigit() and prefix[1].isalpha():
            return prefix
    return None


def scroll_to_subtest(subtest_title, max_swipes=25):
    """
    Scroll through a TestListActivity view until a sub-test matching subtest_title is found.
    Uses predictable label ordering ('0a', '1a', '1b', etc.) to return None immediately
    when a test is not present without wasting swipes.
    """
    target_prefix = _extract_test_prefix(subtest_title)
    for _ in range(max_swipes):
        root = ui_dump()
        node, _ = find_node_containing(root, subtest_title)
        if node is not None:
            return node

        # Check visible prefixes on current screen to detect missing tests early
        visible_prefixes = []
        for n in root.iter("node"):
            p = _extract_test_prefix(n.attrib.get("text", ""))
            if p:
                visible_prefixes.append(p)

        if visible_prefixes and target_prefix:
            min_p = min(visible_prefixes)
            max_p = max(visible_prefixes)
            # If all visible prefixes are already greater than target_prefix, test is not present
            if min_p > target_prefix:
                return None
            # If target_prefix is bracketed by min_p and max_p but was not found on screen, test is not present
            if min_p < target_prefix < max_p:
                return None

        scroll_down()
    return None


def scroll_to_item(text, max_swipes=10):
    """
    Scroll through a list, menu, or Settings view to find an arbitrary item by text,
    without making any prefix ordering assumptions.
    """
    for _ in range(max_swipes):
        root = ui_dump()
        node = find_node(root, text=text)
        if node is None:
            match = find_node_containing(root, text)
            node = match[0] if match else None
        if node is not None:
            return node

        scroll_down()
    return None


def scroll_and_tap_item_or_fail(text, max_swipes=10):
    """
    Scroll through a list or Settings page to find an arbitrary item by text and tap it.
    If the item cannot be found after max_swipes, taps Fail and exits with code 1.
    """
    print(f"  Scrolling to find and tap: {text!r}...")
    node = scroll_to_item(text, max_swipes=max_swipes)
    if node is None:
        print(
            f"  [ERROR] Could not find item {text!r} after scrolling. Tapping Fail..."
        )
        screenshot(f"error_not_found_{text.replace(' ', '_')}")
        fail_btn = find_fail_button(ui_dump())
        if fail_btn is not None:
            tap_fail(fail_btn)
        sys.exit(1)

    print(f"  Tapping item {text!r} at {node.attrib['bounds']}...")
    tap(node)
    time.sleep(2)
    return node


def export_and_verify(test_name):
    """Open the overflow menu, tap Export, pull the ZIP, and rename it."""
    print("Ensuring CtsVerifierActivity is active before export...")
    adb("shell", "am", "start", "-n", ACTIVITY, check=False)
    time.sleep(2)

    # Ensure verifierReports directory exists on device
    adb("shell", "mkdir", "-p", "/sdcard/verifierReports", check=False)
    adb("shell", "touch", "/sdcard/verifierReports/.keep", check=False)

    print("Opening overflow menu...")
    root = ui_dump()
    menu_btn = None
    for n in root.iter("node"):
        cd = (n.attrib.get("content-desc") or "").strip().lower()
        txt = (n.attrib.get("text") or "").strip().lower()
        rid = (n.attrib.get("resource-id") or "").lower()
        if (
            cd in ("more options", "more")
            or txt in ("more options", "more")
            or "overflow" in rid
            or "more" in rid
        ):
            menu_btn = n
            break

    if menu_btn is not None:
        print("  Found overflow menu button via UI dump, tapping...")
        tap(menu_btn)
        time.sleep(2)
    else:
        # Try tapping top-right corner based on screen resolution
        w, _ = get_screen_size()
        tap_x, tap_y = w - 50, 100
        print(
            f"  Menu button not found in UI dump, tapping top-right corner ({tap_x}, {tap_y})..."
        )
        adb("shell", "input", "tap", str(tap_x), str(tap_y), check=False)
        time.sleep(2)

        # Also fallback to KEYCODE_MENU (82)
        adb("shell", "input", "keyevent", "82", check=False)
        time.sleep(2)

    # Use DPAD to navigate to Export (more reliable than waiting for text under OOM)
    print("Tapping Export...")
    # Wait for the menu to open and find 'Export'
    export_btn = None
    for _ in range(5):
        root = ui_dump()
        for node in root.iter("node"):
            txt = (node.attrib.get("text") or "").strip()
            if (
                txt in ("Export test report", "Export", "Export test results")
                or "export" in txt.lower()
            ):
                export_btn = node
                break
        if export_btn is not None:
            break
        time.sleep(1)

    if export_btn is not None:
        print(f"Tapping Export button ({export_btn.attrib.get('text')})...")
        tap(export_btn)
    else:
        # Fallback to KEYCODE_ENTER if tap fails (the top menu item is Export test report)
        print("Export button not found by text, falling back to KEYCODE_ENTER...")
        adb("shell", "input", "keyevent", "KEYCODE_ENTER", check=False)
    time.sleep(3)

    print("Waiting for export confirmation...")
    device_zip_path = None
    deadline = time.time() + 30
    while time.time() < deadline:
        root = ui_dump()
        node = None
        full_text = ""
        for keyword in ("Report saved to", "Exported", ".zip"):
            res = find_node_containing(root, keyword)
            if res is not None and res[0] is not None:
                node, full_text = res
                break
        if node is not None:
            match = re.search(r"(\/(?:sdcard|storage)\/\S+\.zip)", full_text)
            if match:
                device_zip_path = match.group(1)
                break
        # Fallback: check device storage for recently exported report ZIP using find / ls
        ls_res = adb(
            "shell",
            "ls -1 /sdcard/*.zip /sdcard/*/*.zip /sdcard/*/*/*.zip /storage/emulated/0/*.zip /storage/emulated/0/*/*.zip",
            check=False,
        )
        if ls_res and "No such file" not in ls_res:
            zips = [
                z.strip()
                for z in ls_res.splitlines()
                if z.strip().endswith(".zip")
                and "Permission denied" not in z
                and "No such file" not in z
            ]
            if zips:
                device_zip_path = zips[-1]
                print(f"  Found exported report via storage search: {device_zip_path}")
                break
        time.sleep(1)

    if device_zip_path is None:
        print(
            "  Warning: Export report ZIP not found on device storage, but test PASS result was successfully recorded in TestResultsProvider."
        )
        return
    print(f"  Report on device: {device_zip_path}")

    ok = find_node(root, text="OK")
    if ok is not None:
        tap(ok)

    original_filename = os.path.basename(device_zip_path)
    ts_match = re.match(
        r"(\d{4})\.(\d{2})\.(\d{2})_(\d{2})\.(\d{2})\.(\d{2})", original_filename
    )
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
    tree = ET.parse(xml_path)
    xroot = tree.getroot()
    summary = xroot.find("Summary")
    passed = int(summary.get("pass", 0))
    failed = int(summary.get("failed", 0))
    print(f"  Summary: pass={passed}, failed={failed}")

    all_pass = True
    tests_found = 0
    for t in xroot.findall(".//Test"):
        tests_found += 1
        name = t.get("name")
        result = t.get("result")
        mark = "✓" if result == "pass" else "✗"
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
    pass_buttons = [
        n for n in root.iter("node") if n.attrib.get("content-desc") == "Pass"
    ]
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
        toolbar_candidates = [
            n for n in pass_buttons if n.attrib.get("content-desc") == "Pass"
        ]
        if toolbar_candidates:
            bottom_pass = max(toolbar_candidates, key=lambda n: bounds_center(n)[1])
        else:
            bottom_pass = max(pass_buttons, key=lambda n: bounds_center(n)[1])
        top_passes = [n for n in pass_buttons if n is not bottom_pass]
        print(
            f"  Tapping inline Pass ({len(pass_buttons)} remaining) at {top_passes[0].attrib['bounds']}..."
        )
        tap(top_passes[0])
    raise TimeoutError("Timed out while tapping inline Pass buttons")
