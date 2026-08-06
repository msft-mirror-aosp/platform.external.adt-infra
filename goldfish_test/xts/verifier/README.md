# CTS Verifier Automated Test Debugging Guide

This directory contains automated Python scripts that drive CTS Verifier tests on the emulator. Because CTS Verifier tests rely on GUI automation, they are inherently prone to flakiness due to timing, UI element changes, or emulator performance variations on Remote Build Execution (RBE).

Here is a guide to running, debugging, and fixing these tests.

## 1. Running Tests Locally

To reproduce an RBE failure, you can run a specific test locally using the wrapper scripts (`myv1.sh` or `myv.sh`) from your project root. Pass the test target name (derived from the python file name, usually stripping `pass_` and `.py`).

Use `./myv1.sh` for single-test verification or `./myv.sh` for running the full suite or multiple tests.

For reference, the contents of these scripts in the project root are:

**`myv1.sh`:**
```bash
./prebuilts/bazel/linux-x86_64/bazel test -c opt --config=remote --sandbox_debug --nocache_test_results \
                        --config=ants --config=sponge \
                        @goldfish_test//xts:cts-verifier.$1
```

**`myv.sh`:**
```bash
./prebuilts/bazel/linux-x86_64/bazel test -c opt --config=remote --sandbox_debug --nocache_test_results \
                        --config=ants --config=sponge \
                        --flaky_test_attempts=8 \
                        @goldfish_test//xts:cts-verifier
```

```bash
cd /path/to/project/root
./myv1.sh <test_target_name>
# or
./myv.sh <test_target_name>

# Example:
# For third_party/adt-infra/goldfish_test/xts/verifier/pass_tiles_tile_service_request_test.py
./myv1.sh tiles_tile_service_request_test
```

## 2. Inspecting the Logs

If a test fails, Bazel will print the path to the test log:

```
FAIL: ... (see /path/to/execroot/.../testlogs/.../test.log)
```

**What to look for in the log:**
1. **Python Exception Traceback:** The end of the log will usually contain the Python traceback indicating exactly where the test failed (e.g., `TimeoutError: Timed out waiting for enabled button`).
2. **Screenshot References:** The framework takes screenshots at various steps (`[screenshot] 01_app_launched.png`). These can be extracted from the bazel test outputs directory (sibling to `test.log`) to visually inspect what was on screen before the failure.
3. **ADB Errors:** Watch out for `adb failed to run` or device offline errors, which indicate infra/emulator crashes rather than test logic issues.

## 3. Debugging UI State

When a test cannot find an element, the best approach is to pause the test and dump the UI tree.

Modify the failing python script right before the failure point:

```python
import sys
import xml.etree.ElementTree as ET

# ... existing code ...

# Right before the element you are trying to find:
root = ui_dump()
ET.dump(root)
sys.exit(1)
```

Run the test again. The `test.log` will now contain the complete XML hierarchy of the current screen. Look for the `text`, `content-desc`, `class`, and `bounds` attributes of the element you are targeting.

*(Note: Bazel aggressively caches file reads in external workspaces. If your script edits aren't being picked up, try `touch third_party/adt-infra/goldfish_test/xts/BUILD.bazel` to force a rebuild).*

## 4. Common Flakiness Issues & Fixes

### Flaky Navigation
The CTS Verifier app can sometimes take a long time to load its massive list of tests. `navigate_to(TEST_NAME)` might fail if the list isn't fully rendered.
**Fix:** Wrap the initial navigation in a retry loop that force-stops the app if it hangs:

```python
for attempt in range(3):
    try:
        navigate_to(TEST_NAME)
        break
    except RuntimeError:
        adb("shell", "am", "force-stop", "com.android.cts.verifier")
        time.sleep(2)
        adb("shell", "am", "start", "-n", "com.android.cts.verifier/.CtsVerifierActivity")
        time.sleep(5)
```

### Multiple Buttons with the Same Text
If a test involves scrolling down a long list of steps, previous "Pass" or "Start request" buttons might remain in the View hierarchy, causing the script to tap the wrong one.
**Fix:** Ensure you are selecting the *last* matching button on screen, or restrict your search bounds. For example, `wait_for_button` can be modified to accept an `index=-1` parameter.

### Strict Text Matching
Smart quotes (`Don’t` vs `Don't`) or unexpected capitalization can break exact string matches.
**Fix:** Prefer case-insensitive substring matching (`"don" in t.lower() and "add tile" in t.lower()`).

### Swipe vs Tap
If an element expects a drag or fling (like removing a Recents task), a very fast swipe (default duration ~100ms) might register as a tap.
**Fix:** Increase the swipe duration to `300` milliseconds so the OS interprets it correctly:
```python
adb("shell", "input", "swipe", x1, y1, x2, y2, "300")
```

### Screen Off / On
Some tests explicitly require the screen to be turned off and on.
**Fix:** Use keyevents to simulate power cycles, but make sure to wait long enough (e.g., 8 seconds) and send a `KEYCODE_MENU` (82) or swipe to unlock the lock screen.
```python
adb("shell", "input", "keyevent", "KEYCODE_SLEEP")
time.sleep(8)
adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
time.sleep(2)
adb("shell", "input", "keyevent", "82") # Unlock
```

## 5. Handling Device Reboots (`reboot_and_wait`)

Some CTS Verifier tests (e.g., Device Admin Policy Serialization, Device Admin Screen Lock, Device Admin Uninstall) require an intentional device reboot during execution to verify policy persistence across reboots.

### Important Rule
Because the CTS Verifier test harness uses ADB to monitor device liveliness and maintain the emulator session, executing `adb shell reboot` directly will cause the ADB socket to close unexpectedly and fail the test.

**Tests must always use `reboot_and_wait()` rather than calling `adb shell reboot` directly:**

```python
from cts_common import setup, navigate_to, tap, reboot_and_wait, export_and_verify

setup()
navigate_to("Policy Serialization Test")

# Execute pre-reboot UI steps...
tap(apply_policy_btn)
tap(activate_admin_btn)

# Use reboot_and_wait() instead of raw 'adb shell reboot':
reboot_and_wait()

# Re-open CtsVerifier and check persisted policies post-reboot...
navigate_to("Policy Serialization Test")
export_and_verify("Policy Serialization Test")
```

`reboot_and_wait()` automatically issues the reboot, waits for `adbd` to disconnect and reconnect, verifies `sys.boot_completed == 1`, and unlocks the device screen post-reboot. **IMPORTANT:** Because raw `adb shell` commands drop their connection when a device reboots, any CTS Verifier test that calls `reboot_and_wait()` MUST be executed via `ets-verifier` (`@goldfish_test//xts:ets-verifier.<module>`) rather than `cts-verifier`. Tradefed (`ets-verifier`) natively supervises ADB disconnection and reconnection across 0, 1, or N reboots.

