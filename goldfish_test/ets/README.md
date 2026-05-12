# Emulator Test Suite

The Emulator Test Suite is a set of end to end tests for the goldfish emulator
that are run via
[Tradefed](https://g3doc.corp.google.com/company/teams/tradefed/index.md?cl=head).

## TL;DR

The easiest way to run ETS is via bazel:

```sh
bazel test --config=ants --config=sponge @goldfish_test//ets:presubmit

...

INFO: Build completed successfully, 9424 total actions
@goldfish_test//ets:presubmit                                            PASSED in 140.8s

Executed 1 out of 1 test: 1 test passes.
There were tests whose specified size is too big. Use the --test_verbose_timeout_warnings command line option to see which ones these are.
INFO: Streaming build results to: https://fusion2.corp.google.com/invocations/e518676f-33f1-4db4-a54e-1a8a9f54f464
```

The link on the final line will take you to more detailed results/logs.

## Overview

### Why Tradefed?

[Tradefed](https://g3doc.corp.google.com/company/teams/tradefed/index.md?cl=head)
is the test harness for all of xTS as has a number of features our pytest
implementation was lacking (handling of lost devices, cancelling a run early and
getting partial results) as well a large number of existing libraries (ADB
interactions, loading APKs, etc).

It is very dynamic in that it discovers module config files upon startup so new
tests can be added without needing to recompile tradefed itself. Additionally
all of our tooling already works with running tradefed and interpreting the
results.

### How is the Emulator Test Suite Built?

Like other xTS variants, the Emulator Test Suite is packaged a zip file. For our
use-case, we start with a prebuilt version of tradefed and repackage that zip
with our specific test files. The contents includes:

-   Tradefed prebuilt files (jars, shell scripts, etc)
-   Host side test jars
-   Module config files
-   On device test APK files
-   Support APK files (AnimateBox)

### How does bazel run the tests?

To aid in the running the large sequence of events that need to take place,
bazel uses
[test sequencer](https://g3doc.corp.google.com/wireless/android/devtools/emulator/tradefed_analysis/test_loop_v2/test_seq/docs/QuickStart.md?cl=head)
to do the heavy lifting. The bazel rule itself has the following dependencies:

-   Built on the fly
    -   Emulator
    -   Emulator Test Suite
-   Downloaded from GCS
    -   System Image
    -   Build/Platform tools
    -   Test Sequencer

The test itself is python code which accepts flags from bazel of the paths to
each of the above components. This is used to construct the test sequencer
config file, as well as run test sequencer.

The primary test sequencer config will do the following:

-   Extract any dependencies which are within zip files
-   Create the ANDROID_HOME directory
-   Create an avd
-   Boot the emulator
-   Run the emulator test suite
-   Translate the output result file into one bazel can consume.

If the test was run with `--config=sponge --config=ants` the result and logs
will be uploaded to sponge/test fusion and a link to these will be printed.
Without those flags the files seem to disappear in the bazel ether.

### Presubmit vs Postsubmit

The tests currently run in both presubmit and postsubmit. While there are two
separate bazel targets, `@goldfish_test//ets:presubmit` and
`@goldfish_test//ets:postsubmit` they currently resolve to the same tests. At
some time in the future the post-submit target will likely contain more, longer
running tests.

## Futher Information

[ETS Codelab](https://source.corp.google.com/h/googleplex-android/platform/superproject/emu-main-next/+/emu-main-next:third_party/adt-infra/goldfish_test/ets/codelab.md)
