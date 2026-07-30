# Developing CTS-Verifier Test Automation

This document defines the canonical guidelines, architecture, and step-by-step workflow for developing automated test scripts for CTS Verifier in the Goldfish test framework.

---

## 1. Core Philosophy & Terminology

### Key Concepts & Definitions
- **Category (`TestListItem.newCategory`)**: Top-level section header in CTS Verifier (e.g., `DEVICE ADMINISTRATION`, `MANAGED PROVISIONING`, `AUDIO`, `CAMERA`).
- **Test Item (`TestListItem.newTest`)**: Individual test submodule listed under a category (e.g., `Screen Lock Test`, `Policy Serialization Test`, `Device Admin Tapjacking Test`).
- **TestBuilder**: Interactive generator and snapshot recorder (`automation_dev/test_builder.py`) that executes inside the emulator environment over ADB, recording UI state transitions and producing clean `pass_<test_name>_test.py` scripts.

---

## 2. Developer Workflow & Bazel Targets

### Key Bazel Targets & CLI Commands

| Action | Bazel Target | `emu-dev-cli` Command | Description |
| :--- | :--- | :--- | :--- |
| **Collect Test Items & Coverage** | `@goldfish_test//xts:cts-verifier-automation-dev` | `emu-dev-cli cts run-cts-verifier --collect-tests` | Boots emulator, scans live UI, and generates `cts_verifier_test_labels.json` with automation coverage. |
| **Develop Test Automation** | `@goldfish_test//xts:cts-verifier-automation-dev` | `emu-dev-cli cts run-cts-verifier --test-builder-mode --module "Screen Lock Test"` | Launches interactive TestBuilder session for a specific test label (e.g. `"Screen Lock Test"`). |
| **Run Individual Automated Test** | `@goldfish_test//xts:ets-verifier.<slug>` | `emu-dev-cli cts run-cts-verifier --module <slug>` | Runs hermetic automated test via Tradefed for a specific module (e.g. `device_admin_tapjacking_test`). |
| **Run Individual Test on RBE** | `@goldfish_test//xts:ets-verifier.<slug>` | `emu-dev-cli cts run-cts-verifier --rbe --module <slug>` | Runs hermetic automated test on Remote Build Execution (RBE). |
| **Run All Automated Tests** | `@goldfish_test//xts:ets-verifier` | `emu-dev-cli cts run-cts-verifier --all` | Runs the full ETS-Verifier automated test suite. |
| **Run All Automated Tests on RBE** | `@goldfish_test//xts:ets-verifier` | `emu-dev-cli cts run-cts-verifier --rbe --all` | Runs the full ETS-Verifier automated test suite on RBE. |

---

### Step-by-Step Execution Guide

#### Step 1: Discover Test Items & Automation Coverage
Run the test collector target to inspect all rendered categories, test items, and current test coverage:
- **CLI Command**:
  ```bash
  $ emu-dev-cli cts run-cts-verifier --collect-tests
  ```
- **Direct Bazel Target**:
  ```bash
  $ bazel run @goldfish_test//xts:cts-verifier-automation-dev -- --collect_tests --window
  ```
This updates `third_party/adt-infra/goldfish_test/xts/verifier/cts_verifier_test_labels.json` with the full category tree and marks every test item with `"automated": true/false` and its corresponding script path.

#### Step 2: Launch Interactive TestBuilder Mode
To develop or record automation for an untested test item (e.g., `"Screen Lock Test"`):
- **CLI Command**:
  ```bash
  $ emu-dev-cli cts run-cts-verifier --test-builder-mode --module "Screen Lock Test"
  ```
- **Direct Bazel Target**:
  ```bash
  $ bazel run @goldfish_test//xts:cts-verifier-automation-dev -- --dev_mode --window --script run_screen_lock_test.sh
  ```

This will:
1. Boot an emulator instance with GUI window enabled.
2. Install `CtsVerifier.apk` and launch the app.
3. Automatically navigate into `"Screen Lock Test"`.
4. Present an interactive REPL prompt (`TestBuilder>`) with snapshot IDs and clickable elements.

During an interactive `TestBuilder` session, every interaction (tap, key event, swipe, pass) automatically appends structured element metadata and state information to **`session_trace.json`** inside `automation_dev/sessions/<test_slug>/`:
```json
{
  "step": 3,
  "activity": "com.android.cts.verifier.admin.ScreenLockTestActivity",
  "action": "tap_element",
  "interacted_element": {
    "text": "Force Lock",
    "content_desc": "",
    "resource_id": "com.android.cts.verifier:id/da_force_lock_button",
    "class": "android.widget.Button",
    "package": "com.android.cts.verifier",
    "bounds": "[557,1436][882,1684]"
  },
  "resulting_snapshot": "04_force_lock.xml"
}
```
This trace log provides an exact record of every XML element interacted with and every screen state reached during probing. Once probing is complete, the agent can inspect `session_trace.json` to determine the exact sequence of `wait_for()` state transitions required for the final automation script.

#### Step 3: Record UI Actions & Transitions
In the `TestBuilder>` prompt, execute actions sequentially:
- Enter item numbers (e.g. `1`) or text commands (e.g., `tap Force Lock`, `tap OK`) to interact with buttons.
- Send key events (`key 82` to unlock, `key KEYCODE_WAKEUP`).
- Send system commands or sleep delays (`sleep 2`).
- Upon reaching the pass state, type `pass` to finalize recording and auto-generate `pass_<test_name>_test.py`.

#### Step 4: Finalize & Register Test Target
1. Review the generated `pass_<slug>_test.py` script.
2. Create the shell wrapper `run_<slug>_test.sh`:
   ```bash
   #!/bin/bash
   set -e
   python3 $(dirname "$0")/pass_<slug>_test.py
   ```
3. Test hermetic execution via Bazel:
   - **CLI Command**:
     ```bash
     $ emu-dev-cli cts run-cts-verifier --module <slug>
     ```
   - **Direct Bazel Target**:
     ```bash
     $ bazel run @goldfish_test//xts:cts-verifier.<slug>
     ```

---

## 3. Agent Execution & Development Guidelines (Strict Alignment Protocol)

When an AI Agent is developing or recording test automation using `TestBuilder`, it MUST strictly adhere to the following rules:

### 📜 Rule 1: Full Context Reading at Every State Transition
- **Comprehensive Page Analysis**: At every step and screen transition (including alert dialogs, test activities, system settings, or lock screens), the agent **MUST read all text nodes, instructions, titles, body descriptions, and button labels** on the screen before taking any action.
- **Understand Test Requirements**: Read and parse the test's instruction text to understand the exact pre-requisites (e.g. *"Make sure screen lock is NOT set to None"*), actions (e.g. *"Click Force Lock button"*), and verification criteria required for a valid test run.
- **Do Not Guess or Rush**: Never tap buttons blindly without first reading and verifying what the screen is asking for.

---

### 🛡️ Rule 2: Strict Adherence to Test Instructions ("No Cheating")
- **Authentic Test Execution**: The agent **MUST strictly follow the step-by-step test instructions** to execute the real test logic and achieve a genuine pass state.
- **Zero Force-Passing / Zero Cheating**: Never bypass required test steps or force-pass a test by directly tapping the green Pass button (`id="pass_button"`) without actually executing the required test actions (such as setting up device admin policies, setting screen lock passcodes, or verifying system behavior).
- **Handle Multi-Step Workflows Realistically**: If a test requires opening Android Settings, configuring a lock pattern, locking the device, and unlocking it to verify policy enforcement, the agent must perform each step realistically using ADB commands and UI interaction.

---

### 🔍 Rule 3: State Transition Verification & Explicit `wait_for()` Synchronization
- **Mandatory `wait_for()` State Synchronization**: **Every single state transition MUST use `wait_for()`** to deterministically confirm the UI is ready before performing any action. Never rely solely on fixed `time.sleep()` delays between actions.
- **State Helpers for Device Events**:
  - Use `wait_for(text=...)` or `wait_for(content_desc=...)` for screen elements and buttons.
  - Use `wait_for_screen_off()` when testing `lockNow()` or screen timeout policies.
  - Use `wait_for_keyguard_showing()` after waking the screen before entering PINs or passcodes.
- **Element Interactivity & `enabled="true"` Verification**: Many Android UI controls (such as `Enable admin`, `Uninstall`, or `Pass` buttons) are rendered in the XML tree immediately with `enabled="false"` until asynchronous broadcasts or permission grants complete. Always ensure `wait_for()` checks `node.attrib.get("enabled", "true") == "true"` before returning so actions are only performed on clickable, enabled elements.
- **Post-Action Dump Inspection**: After executing any action (e.g., `1`, `tap Force Lock`, `key 82`), inspect the new screen dump (`ui_dump()`) to confirm the screen actually transitioned to the expected next state.
- **Handle Unexpected Dialogs**: If an unexpected system dialog appears (e.g. permissions, device admin activation, notification access), read its text, handle it appropriately according to the test flow, and continue.

---

### 📝 Rule 4: Self-Documenting Script Generation
- **Explain Intent in Generated Scripts**: Every generated `pass_<slug>_test.py` script must include clear inline comments explaining *why* each step is performed, directly referencing the test instructions read during development.

---

### 🆘 Rule 5: Proactive Alignment & Help Escalation When Stuck
- **Recognize Roadblocks Early**: If the agent encounters an unexpected UI state, missing prerequisite, ambiguous test instruction, device configuration error, or an unexpected dialog that prevents clean test progression, it **MUST NOT guess blindly, loop indefinitely, or force-pass the test**.
- **Ask for Human Guidance**: The agent must proactively pause, issue a ping or ask the user for help, and clearly communicate:
  1. **Current Context & UI State**: The current activity, screen title, and all visible text/elements.
  2. **Reason For Being Stuck**: The exact roadblock, ambiguity, or unexpected behavior encountered.
  3. **What Is Needed To Continue**: Specific options, clarification, or manual intervention required to proceed.

---

## 4. Best Practices & Coding Standards

1. **State-Driven Synchronization (Anti-Flake Standard)**:
   - Always call `wait_for()` or specialized wait helpers before interacting with elements to ensure zero race conditions between UI animations, system server calls, and test actions.
   - Always check for initial instruction dialogs (`"OK"`, `"Allow"`) and handle dismissals gracefully with `wait_for(text="OK")`.
   - Use `find_node(root, text="...")` or `find_node_containing(root, "...")` rather than hardcoding coordinates whenever possible.

2. **Timing & Device Stability**:
   - Allow sufficient delay after launching activities or triggering device admin policies before calling `ui_dump()`.
   - Never poll `ui_dump()` too rapidly without delays to prevent uiautomator OOM crashes.

3. **Deterministic Prerequisite Polling**:
   - When installing helper APKs (such as `CtsEmptyDeviceAdmin.apk`) or modifying system states over ADB, never rely on arbitrary fixed sleep timers (`time.sleep(...)`). Instead, poll the system state explicitly (e.g., polling `adb shell pm list packages <pkg>` every 2 seconds until package registration is confirmed by `PackageManagerService`).

4. **Reboot & Boot Synchronization**:
   - When a test requires rebooting the emulator, always use `reboot_and_wait()` from `cts_common.py`. It safely orchestrates `adb shell reboot -> adb wait-for-device -> sys.boot_completed -> unlock screen (keyevent 82)` without disrupting the Bazel test runner environment.

5. **Pass Verification & Verification Export**:
   - Conclude every test script with `tap_pass()` and `export_and_verify()` to ensure CTS Verifier records the test pass state and exports results cleanly.

---

## 5. Maintenance & Coverage Matrix
- Keep `cts_verifier_test_labels.json` updated by running `emu-dev-cli cts run-cts-verifier --collect-tests`.
- Ensure all new test scripts follow the `pass_<name>_test.py` naming convention for automatic coverage tracking.

---

## 6. Testing for Regressions on RBE
Before submitting any automation changes or framework refactoring, **make sure to run `ets-verifier` on all tests on RBE to make sure everything passes**:

- **CLI Command**:
  ```bash
  $ emu-dev-cli cts run-cts-verifier --rbe --all
  ```
- **Direct Bazel Command**:
  ```bash
  $ bazel test -c opt --config=remote --sandbox_debug --nocache_test_results \
      --config=ants --config=sponge --flaky_test_attempts=8 \
      @goldfish_test//xts:ets-verifier
  ```

Running the full `@goldfish_test//xts:ets-verifier` suite on RBE verifies that all automated test modules (including reboot tests) complete successfully in remote headless VMs without regressions.
