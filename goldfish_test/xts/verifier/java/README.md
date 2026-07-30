# CTS Verifier

ETS can be used to run the CTS Verifier. This is largely still a work in
progress.

The easiest way to do so is to run:

```sh
bazel test --config=ants --config=sponge @goldfish_test//xts:ets-verifier
```

## Overview

The test sequencer configuration
[here](https://source.corp.google.com/h/googleplex-android/platform/superproject/emu-main-next/+/emu-main-next:third_party/adt-infra/goldfish_test/xts/ets_verifier_config.py)
will start the emulator, install the CTS Verifier APK, run the needed ADB
commands and kick off the ETS modules. These include both python and Kotlin.

## ClockTest ETS Module

The ClockTest ETS module currently only runs `Show Alarms Test`. The code can be
found
[here](https://source.corp.google.com/h/googleplex-android/platform/superproject/emu-main-next/+/emu-main-next:third_party/adt-infra/goldfish_test/xts/java/com/android/tools/e2etests/clock/ClockTest.kt)

This is still a work in progress, but as a general guideline:

-   Use: `@get:Rule val ctsVerifierRule = CtsVerifierResource()` to restart the
    verifier app before your test and grab the result zip after.

-   Run one verifier test per `@Test` function.

-   Try to do best effort verification

    -   Do not just click the pass button blindly
    -   Verify some expected UI components exist, but no need for pixel-by-pixel
        verification.

-   The `@Test` should fail if the underlying CTS Verifier test fails.

-   Use the `takeScreenshot()` function to help offline debugging of failures.

The final result zips will be pulled by the testing framework.
