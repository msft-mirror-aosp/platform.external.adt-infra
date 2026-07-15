# CTS Verifier

ETS can be used to run the CTS Verifier. This is largely still a work in
progress.

The easiest way to do so is to run:

```sh
bazel test --config=ants --config=sponge @goldfish_test//ets:cts_verifier
```

## Overview

The test sequencer configuration
[here](https://source.corp.google.com/h/googleplex-android/platform/superproject/emu-main-next/+/emu-main-next:third_party/adt-infra/goldfish_test/ets/verifier_cfg.py)
will start the emulator, install the CTS Verifier APK, run the needed ADB
commands and kick of the CtsVerifier ETS module.

## CtsVerifier ETS Module

The CtsVerifier ETS modules currently only runs `Show Alarms Test`. The code can
be found
[here](https://source.corp.google.com/h/googleplex-android/platform/superproject/emu-main-next/+/emu-main-next:third_party/adt-infra/goldfish_test/ets/java/com/android/tools/e2etests/ctsverifier/CtsVerifierTest.kt)

This is still a work in progress, but as a general guideline:

-   Run one verifier test per `@Test` function.
-   Try to do best effort verification
    -   Do not just click the pass button blindly
    -   Verify some expected UI components exist, but no need for pixel-by-pixel
        verification.
-   The `@Test` should fail if the underlying CTS Verifier test fails.
-   Use the `takeScreenshot()` function to help offline debugging of failures.

The final result zip will be pulled by the testing framework but this is not yet
complete.
