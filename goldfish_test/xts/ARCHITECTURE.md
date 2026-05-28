# Component: Emulator Compatibility Tests

**Role:** Defines CTS (Compatibility Test Suite) and dEQP (Draw Elements Quality Program).
**Location:** `third_party/adt-infra/goldfish_test/cts`
**Namespace:** N/A (Build rules and test scripts)

## Integration Guide
| Target | Description |
| :--- | :--- |
| `:cts` | Runs Android CTS modules against the emulator. |
| `:cts.<module>` | Runs a single Android CTS module. (e.g., :cts.CtsUsbTests) |
| `:deqp` | Runs dEQP graphics conformance tests against the emulator. |

## Critical Infrastructure
* **Test Runners:**
    *   `run_cts.py`: Helper script to execute CTS/dEQP plans.
* **Data Dependencies:** Tests depend on full system images (`@android16k-x86_64//:system_image`, etc.) and a mock SDK (`//emulator/sdk`).
* **Environment:** Sets up a controlled environment (`ANDROID_SDK_ROOT`, `ANDROID_AVD_HOME`) to ensure reproducibility.

## Dependencies
* **Binaries:** `//emulator/launcher` (The artifact under test).
* **System Images:** External Bazel repositories providing Android system images.
* **SDK:** `//emulator/sdk`.

## Threading Model
* **Test Execution:** Tests typically run as separate processes (Bazel sandboxing). Parallelism is managed by Bazel.
