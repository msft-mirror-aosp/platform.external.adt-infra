# AEMU End-to-End Input Tests

This directory contains end-to-end tests for verifying input event delivery and handling in the Android Emulator (AEMU).

## Overview

The goal of these tests is to ensure that input events sent from the host (or simulated via gRPC) are correctly delivered through the emulator's VirtIO input devices to the Android guest OS, and that they result in the expected Android `MotionEvent` and `KeyEvent` objects.

These tests are critical for verifying the integrity of the input stack, including coordinate scaling, multi-touch Protocol B handling, and device identification.

## Architecture

The testing infrastructure consists of the following components:

1.  **JUnit Tests**: Running inside the Android guest. They orchestrate the test flow.
2.  **Event Injection**: Tests use the `EmulatorController` gRPC service to stream input events (`KeyboardEvent`, `TouchEvent`, `MouseEvent`, `PenEvent`, `AndroidEvent`) into the emulator.
3.  **Raw Event Observation (`EventObserver`)**: A helper class that runs `getevent` in the background to capture raw Linux input events from `/dev/input/eventN` nodes. This allows verifying that the emulator is generating the correct low-level hardware events.
4.  **UI Event Verification (`InputTestActivity`)**: A simple activity that captures and logs `onTouchEvent`, `onKeyDown`, and `onGenericMotionEvent` calls. Tests verify that Android interprets the raw events as expected high-level events.

### Fluent Assertions

The tests use extension functions on `List<RawEvent>` (defined in `EventObserver.kt`) to provide fluent assertions like:
```kotlin
sharedObserver.waitForEvents(2, 1000) {
    // trigger events
}
.assertSizeAtLeast(2)
.assertContains(code, value)
```

## Test Classes

*   **`KeyboardInputTest`**: Verifies key down/up events and text delivery.
*   **`TouchInputTest`**: Verifies multi-touch sequences, coordinate scaling, and pointer tracking.
*   **`MouseInputTest`**: Verifies mouse clicks and drags.
    *   *Note*: Hover events (move without click) are currently ignored due to emulator limitations (Bug: 515726317).
*   **`AndroidInputTest`**: Verifies injection of raw `evdev` events via `AndroidEvent`.
*   **`PenInputTest`**: Verifies stylus and eraser events.
    *   *Note*: Currently ignored due to event delivery issues on phone profiles (Bug: 515725062).

## Running the Tests

The tests are run via Bazel and Tradefed as part of the Emulator Test Suite (ETS). According to [codelab.md](../../../../../../codelab.md), the easiest way to run them is via the presubmit target:

```bash
# On Linux
prebuilts/bazel/linux-x86_64/bazel test @goldfish_test//ets:presubmit --test_output=all

# On Mac
prebuilts/bazel/darwin-x86_64/bazel test @goldfish_test//ets:presubmit --test_output=all
```

To run against an already running emulator (for faster iteration):
```bash
prebuilts/bazel/linux-x86_64/bazel test @goldfish_test//ets:external_presubmit
```

To launch the emulator with the required flags for external tests, use:
```bash
bazel run @goldfish//emulator/launcher:launch_emulator -- -grpc-allowlist hardware/generic/goldfish/emulator/libs/grpc_security/testdata/test_allow_list.json -verbose-grpc -verbose -vmodule 'qemu_display=2,virtio_bridge*=1,key*=2'
```
*   **`-grpc-allowlist`**: This flag is required to allow gRPC connections without authentication (using the test allow list).
*   **`-vmodule`**: This flag can be used to get detailed logging related to the input layer (e.g., `qemu_display`, `virtio_bridge`).

Detailed logs (including emulator output and logcat) can be found in the `bazel-testlogs` directory after the run:
`bazel-testlogs/external/goldfish_test+/ets/presubmit/test.outputs/results/`

## Presubmit Integration

These tests are enabled in the presubmit suite via the filter in [presubmit.xml](../config/presubmit.xml):
```xml
<option name="include-filter" value="InputTest" />
```
This filter ensures that test classes or modules matching "InputTest" are included in the run.
