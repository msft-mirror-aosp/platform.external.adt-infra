# dEQP Runner ETS Tests

This directory contains the end-to-end host test ([`DeqpRunnerTest.kt`](DeqpRunnerTest.kt)) for executing Khronos dEQP (drawElements Quality Program) tests on the Android Emulator via Tradefed and Mesa's `deqp-runner`.

## Testing Process

1. **Binary, Data & Caselist Preparation**:
   - `DeqpRunnerTest` detects the target emulator ABI (`x86_64` or `arm64-v8a`/`aarch64`) and selects the corresponding prebuilt `deqp-runner` binary and `CtsDeqpTestCases/deqp-binary64*` executable.
   - It pushes the `CtsDeqpTestCases/` data directories (`gles2`, `gles3`, `gles31`, `internal`, `skips`, `vulkan`), the binaries, and the sanitized caselist from [`testcases/presubmit.txt`](testcases/presubmit.txt) to `/data/local/tmp/CtsDeqpTestCases` on the device.

2. **On-Device Execution**:
   - `DeqpRunnerTest` invokes `deqp-runner` on the device to execute the dEQP test cases in parallel against `deqp-binary64` and write output artifacts to `/data/local/tmp/CtsDeqpTestCases/test_out`.

3. **Result Verification & Logging**:
   - After `deqp-runner` completes, `DeqpRunnerTest` pulls the generated `results.csv`, `failures.csv`, device info logs, and any failure `.log` / `.qpa` files from `/data/local/tmp/CtsDeqpTestCases/test_out`.
   - It aggregates the results (`Pass`, `Fail`, `Crash`, `Skip`, `Timeout`, `Incomplete`, `Missing`), attaches the detailed artifacts to the Tradefed test results (`deqp_runner_summary`, `deqp_results_csv`, etc.), prints a summary report, and fails the JUnit test if any unexpected test failures occurred.

## Running the Test

To run `DeqpRunnerTest` against a running emulator instance:

```bash
bazel test --credential_helper_timeout=30s --test_output=streamed --test_arg=--tradefed_args="-m,DeqpRunnerTest" @goldfish_test//ets:external_ets
```

To run with a booted emulator via ETS:

```bash
bazel test --credential_helper_timeout=30s --test_output=streamed --test_arg=--tradefed_args="-m,DeqpRunnerTest" @goldfish_test//ets:ets
```

## More Information

This test setup is based on the standalone `emu_mesa_deqp_runner` project. For details on cross-compiling `deqp-runner`, generating and partitioning full dEQP caselists, and running multi-AVD parallel dEQP test suites, see:

- https://user.git.corp.google.com/kocdemir/emu_mesa_deqp_runner/
