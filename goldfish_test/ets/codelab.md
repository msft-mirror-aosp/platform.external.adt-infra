# Emulator Test Suite Codelab

go/etscodelab

[TOC]

This codelab will guide you through a couple barebones ETS tests, and how to run
them via bazel.

## Before You Start

### Prerequisites

Before you start, make sure you can do the following:

-   Have a Linux or Mac corp machine
    -   ETS will run on windows, but cannot currently be built on windows.
-   Clone the emu-main-next repo
    -   [Local Instructions](https://g3doc.corp.google.com/company/teams/emu-dev/emulator-next/index.md?cl=head)
    -   [Using Cider-G](https://g3doc.corp.google.com/devtools/cider/g3doc/cider-g/getting-started.md?cl=head&polyglot=android)
-   Build the emulator
    -   If `bazel build @goldfish//emulator:release` works you should be set
    -   If not, follow the
        [Local Instructions](https://g3doc.corp.google.com/company/teams/emu-dev/emulator-next/index.md?cl=head)
        to setup needed authentication.

### Glossary

-   [Tradefed](https://g3doc.corp.google.com/company/teams/tradefed/index.md?cl=head):
    the test harness framework used to run ETS
-   [Test Sequencer](https://g3doc.corp.google.com/wireless/android/devtools/emulator/tradefed_analysis/test_loop_v2/test_seq/docs/QuickStart.md?cl=head):
    tool used to run the sequence of tasks needed to run ETS
-   On Device Test: A test that runs on the device, packaged as an APK. Also
    known as an instrumentation test.
-   Host Test: A test that runs on the host. This will be included in a jar file
    in the ets zip file.
-   Module: A group of tradefed tests.

### Testing Philosophy

The main goal with ETS is to learn from issues that were encountered in the
pytest world. The main focus points are:

-   Reduce flakiness
-   Eliminate hangs
-   Reduce overall test runtime

On-device tests are strongly encouraged to help with flakiness. An on-device
test's lifecycle matches that of the emulator. Tradefed will be responsible for
handling a device hang/crash, which it is designed for.

To reduce overall test runtime, with few exceptions the tests will operate on an
already booted emulator, not manipulating the AVD, flags, etc. This is different
than pytest where tests could freely reboot the emulator, however this greatly
increased the runtime as each boot could take 2 minutes, and there was no
coordination between tests.

Different AVDs and flags will be handled via the test sequence and will be in
separate bazel targets to enable parallelism. The tests themselves should
generally be agnostic to the AVD/flags.

In the future when snapshots are supported more details will be added about how
to handle these tests.

Lastly, all of the code is written by someone new to kotlin and on device
testing in general. If you see something that looks wrong, or could be done a
better way, feel free to fix/update it.

### Current Limitations (as of 2026-04-23)

-   Linux: Builds / Runs / passes in pre/postsubmit with good stability
    -   Runs with RBE many times to help ensure stability.
-   Mac ARM: Builds / Runs in pre/postsubmit. Stability is not as good as linux
    but should be improving.
    -   Runs directly on the build bot, so scaling may be a concern.
-   Windows: Runs in post-submit via TLV2 but does not build. Is not currently
    passing
    -   The TLV2 test is enabled by running against a fixed version built on
        linux.
    -   The build is broken as rules_android (needed to build apks) does not
        work on Windows.

## Codelab

### Glance At The Code

The code lives under
[`third_party/adt-infra/goldfish_test`](https://source.corp.google.com/h/googleplex-android/platform/superproject/emu-main-next/+/emu-main-next:third_party/adt-infra/goldfish_test/).
The following directories are of interest:

-   ets: The main location for the tests
-   sequence: Support for code running test sequencer sequences
-   testlib: Library support code
    -   This exists to allow for unit-testing of common libraries. No unit-tests
        are run under the ets directory as they are all intended to run via test
        sequencer.

### Run ETS

The easiest way to run ETS is to use the presubmit test target. This will build
everything, boot an emulator with the required flags, then run the full
presubmit suite. Currently all passing tests are run as part of the presubmit as
the runtime is still very short.

```bash
$ prebuilts/bazel/linux-x86_64/bazel test @goldfish_test//ets:presubmit

...

INFO: Found 1 test target...
Target @@goldfish_test+//ets:presubmit up-to-date:
  bazel-bin/external/goldfish_test+/ets/presubmit
INFO: Elapsed time: 440.442s, Critical Path: 318.45s
INFO: 11429 processes: 2729 internal, 8560 linux-sandbox, 145 worker.
INFO: Build completed successfully, 11429 total actions
@goldfish_test//ets:presubmit                                            PASSED in 142.0s
```

Without any flags you get fairly limited output. To get a simple log in your
console you can add: `--test_output=all`. This will give you more details,
including any logs from the host side, but it is missing the detailed logs. To
view those look in the `bazel-testlogs` directory (output clipped for brevity):

```bash
$ ls -l bazel-testlogs/external/goldfish_test+/ets/presubmit/test.outputs/results/
total 1104
...
-r-xr-xr-x 1 kmagic primarygroup 438453 Apr 23 13:21 0007.goldfish.stdoutstderr.txt
...
dr-xr-xr-x 3 kmagic primarygroup   4096 Apr 23 13:21 0008.tradefed.logs
-r-xr-xr-x 1 kmagic primarygroup   6192 Apr 23 13:21 0008.tradefed.log.txt
dr-xr-xr-x 2 kmagic primarygroup   4096 Apr 23 13:21 0008.tradefed.results
-r-xr-xr-x 1 kmagic primarygroup  61860 Apr 23 13:21 0008.tradefed.stdoutstderr.txt
...
dr-xr-xr-x 3 kmagic primarygroup   4096 Apr 23 13:21 0009.ets_close.logs
-r-xr-xr-x 1 kmagic primarygroup   5611 Apr 23 13:21 0009.ets_close.log.txt
dr-xr-xr-x 2 kmagic primarygroup   4096 Apr 23 13:21 0009.ets_close.results
-r-xr-xr-x 1 kmagic primarygroup   9393 Apr 23 13:21 0009.ets_close.stdoutstderr.txt
...
```

Some files of interest (number prefix may change if the sequence changes):

-   0007.goldfish.stdoutstderr.txt: Output from the emulator process
-   0008.tradefed.logs: Directory of all the logs from running ets
    -   inv_xxxxxxx/device_logcat_test_...txt: Logcat collected during the tests
    -   *.png: Screenshots captured during tests
-   0008.tradefed.stdoutstderr.txt: Output from the ETS process
-   0009.ets_close.*: Same as above, but for the invocation of ETS that closes
    the emulator.

For the curious, the tests that involve closing the emulator run separately to
ensure they run last, and also to avoid issues with tradefed when the device
under test disappears.

### Presubmit Plans

There are currently two plan files that direct tradefed on which modules to run:

- [`presubmit.xml`](https://source.corp.google.com/h/googleplex-android/platform/superproject/emu-main-next/+/emu-main-next:third_party/adt-infra/goldfish_test/ets/java/com/android/tools/config/presubmit.xml)
- [`emu_now_presubmit.xml`](https://source.corp.google.com/h/googleplex-android/platform/superproject/emu-main-next/+/emu-main-next:third_party/adt-infra/goldfish_test/ets/java/com/android/tools/config/emu_now_presubmit.xml)

They currently exist separately to allow writing tests that work on one platform
but not on the other. In these files one can specify which modules/test to
include and exclude.

```xml
    <!-- APK installation error -->
    <option name="exclude-filter" value="CallTest" />
    <option name="include-filter" value="ControlKeysTest" />
    <!-- Not yet passing on emu-next -->
    <option name="exclude-filter" value="ControlKeysTest com.android.tools.e2etests.events.ControlKeysTest#screenshot" />
```

When excluding tests, please add a comment indicating why they are excluded.
There is a unit test to ensure every module in the zip file is either explicitly
included or excluded as this step could easily be forgotten.

[`@goldfish_test//testlib:emu_module_test`](https://source.corp.google.com/h/googleplex-android/platform/superproject/emu-main-next/+/emu-main-next:third_party/adt-infra/goldfish_test/testlib/ets_modules_test.py)


### On Device Tests

#### Code

We will start by taking a look at a simple on device test,
[`BootTest.kt`](https://source.corp.google.com/h/googleplex-android/platform/superproject/emu-main-next/+/emu-main-next:third_party/adt-infra/goldfish_test/ets/java/com/android/tools/e2etests/boot/BootTest.kt).

```kotlin
class BootTest {

  @Test
  fun statusIsBooted() {
    val resp = EmulatorController.defaultDeadline().getStatus(Empty.getDefaultInstance())

    Assert.assertTrue(resp.getBooted())
  }
}
```

On-device tests are just structured like regular JUnit4 tests. If you are
unfamiliar with JUnit4, your favorite search engine / AI agent can help as it is
widely used and there's lots of documentation / examples available.

This test issues the `getStatus()` RPC and asserts the `booted` boolean in the
response is set. As stated above tests should assume the emulator is already
booted. A couple things to note:

-   The `EmulatorController` handles creating and caching the connection.
-   The `defaultDeadline()` is currently 10 seconds. Always set a deadline when
    making RPCs to avoid hangs.

There are more advanced examples in the [Advanced Code](#advanced-code) section.

#### Tradefed Config

The
[`BootTest.config`](https://source.corp.google.com/h/googleplex-android/platform/superproject/emu-main-next/+/emu-main-next:third_party/adt-infra/goldfish_test/ets/java/com/android/tools/e2etests/boot/BootTest.config)
file is the minimal example of what is needed. This file is directly included in
the output zip file. It tells tradefed what APK to load and which package to
test.

```xml
<configuration description="Tests related to the emulator boot">
    <target_preparer class="com.android.tradefed.targetprep.suite.SuiteApkInstaller">
        <option name="cleanup-apks" value="true" />
        <option name="test-file-name" value="BootTest.apk" />
    </target_preparer>

    <test class="com.android.tradefed.testtype.AndroidJUnitTest" >
        <option name="package" value="com.android.tools.e2etests.boot" />
    </test>
</configuration>
```

#### BUILD.bazel

```build
filegroup(
    name = "pkg",
    testonly = 1,
    srcs = [
        ":BootTest.apk",
        ":BootTest.config",
    ],
    visibility = ["//ets:__pkg__"],
)

kt_android_library(
    name = "boot_test_lib",
    testonly = 1,
    srcs = ["BootTest.kt"],
    deps = [
        "//deps/proto:aemu_java_grpc",
        "//ets/java/com/android/tools/e2etests/grpc:grpc_lib",
        "@maven//:androidx_test_core",
        "@maven//:androidx_test_runner",
        "@tradefed//:tradefed_jars",
    ],
)

android_binary(
    name = "BootTest",
    testonly = 1,
    custom_package = "com.android.tools.e2etests.boot",
    manifest = "BootTestManifest.xml",
    manifest_values = {
        "minSdkVersion": "36",
        "targetSdkVersion": "36",
    },
    deps = [":boot_test_lib"],
)
```

Within the
[`BUILD.bazel`](https://source.corp.google.com/h/googleplex-android/platform/superproject/emu-main-next/+/emu-main-next:third_party/adt-infra/goldfish_test/ets/java/com/android/tools/e2etests/boot/BUILD.bazel)
file, the `pkg` rule is used to pull in the needed output files to the zip. If
you add a new test, ensure you add its `pkg` rule to the `//ets:ets_modules`
rule so it is included in the overall zip.

The `android_binary` builds the needed apk, but does not directly support kotlin
code, so you need a `kt_android_library` rule in the deps section. Like most of
the ETS code, these rules were made by an inexperienced author, so may contain
unneeded entries and likely can be cleaned up over time.

### Host Tests

While On-Device tests are preferred, there are some things which can only be
tested off the emulator. One test looks at the discovery files, which are only
present on the host. It should be noted that there are some current host tests
which may be possible to convert to on device tests. The author blames
inconsistent responses from search engines/ai agents.

#### Code

We will look at
[DisplayNameTest.kt](https://source.corp.google.com/h/googleplex-android/platform/superproject/emu-main-next/+/emu-main-next:third_party/adt-infra/goldfish_test/ets/java/com/android/tools/e2etests/discovery/DisplayNameTest.kt)

```kotlin
@RunWith(DeviceJUnit4ClassRunner::class)
class DisplayNameTest : BaseHostJUnit4Test() {

  @Test
  fun testCheckDiscoveryNameMatchesConfigIni() {
    Assert.assertNotNull(getDevice())
    val discovery = findEmulator(getDevice().getSerialNumber())
    Assert.assertNotNull(discovery)
    if (discovery != null) {
      Assert.assertNotNull(discovery.discoveryIni["avd.name"])
      Assert.assertEquals(
        discovery.discoveryIni["avd.name"],
        discovery.configIni["avd.ini.displayname"],
      )
    }
  }
}
```

The first thing to note is that the test class has a parent class and uses a
runner. These pull in useful libraries and features from tradefed, most notably
the `getDevice()` function. This returns a device object that lets you get the
serial number, run adb commands, etc.

#### Tradefed Config

```xml
<configuration description="Host tests checking the display name">
  <test class="com.android.tradefed.testtype.HostTest" >
    <option name="class" value="com.android.tools.e2etests.discovery.DisplayNameTest" />
  </test>
</configuration>
```

This
[DisplayNameTest.config](https://source.corp.google.com/h/googleplex-android/platform/superproject/emu-main-next/+/emu-main-next:third_party/adt-infra/goldfish_test/ets/java/com/android/tools/e2etests/discovery/DisplayNameTest.config)
file is simpler than the on-device test config as the test will be present in an
already loaded jar file, so all that is needed is the class.

#### BUILD.bazel

```build
filegroup(
    name = "pkg",
    srcs = ["DisplayNameTest.config"],
    visibility = ["//ets:__pkg__"],
)

kt_jvm_test(
    name = "display_name_test",
    srcs = ["DisplayNameTest.kt"],
    visibility = ["//ets/java/com/android/tools/e2etests:__pkg__"],
    deps = [
        "//testlib/java/com/android/tools/testlib/emu:discovery",
        "@tradefed//:tradefed_jars",
    ],
)
```

In this
[BUILD.bazel](https://source.corp.google.com/h/googleplex-android/platform/superproject/emu-main-next/+/emu-main-next:third_party/adt-infra/goldfish_test/ets/java/com/android/tools/e2etests/discovery/BUILD.bazel)
file, the `pkg` rule only contains the tradefed config and the test itself is
part of a `kt_jvm_test` rule. Note that trying to run this test with `bazel
test` will not work. The `kt_jvm_test` rule is needed to get the test to compile
correctly, as the author tried `kt_jvm_library` unsuccessfully. The
`kt_jvm_test` must then be included as a runtime dep in
[`ets/java/com/android/tools/e2etests/BUILD.bazel`](https://source.corp.google.com/h/googleplex-android/platform/superproject/emu-main-next/+/emu-main-next:third_party/adt-infra/goldfish_test/ets/java/com/android/tools/e2etests/BUILD.bazel)

```build
# These rules are not meant to be run directly, but as a means to get a single
# jar file containing all of e2e test dependencies. There are conflicts with
# tradefed jar dependencies: e2e_tests_pre comes first in the classpath while
# e2e_tests_post comes last.
java_binary(
    name = "e2e_tests_pre",
    testonly = 1,
    use_launcher = False,
    visibility = ["//ets:__pkg__"],
    runtime_deps = [
        "//ets/java/com/android/tools/e2etests/netsim:netsim_daemon_test",
    ],
)

java_binary(
    name = "e2e_tests_post",
    testonly = 1,
    resource_strip_prefix = "ets/java/com/android/tools/e2etests",
    resources = glob(["config/*.xml"]),
    use_launcher = False,
    visibility = ["//ets:__pkg__"],
    runtime_deps = [
        "//ets/java/com/android/tools/e2etests/discovery:display_name_test",
        "//ets/java/com/android/tools/e2etests/display:adb_screen_cap_test",
        "//ets/java/com/android/tools/e2etests/events:close_emulator_test",
        "//ets/java/com/android/tools/e2etests/files:adb_push_pull_test",
        "//ets/java/com/android/tools/e2etests/netsim:netsim_daemon_test",
        "//ets/java/com/android/tools/e2etests/netsim:netsim_single_device_test",
        "//ets/java/com/android/tools/e2etests/vulkan:vulkan_app_test",
        "//testlib/java/com/android/tools/testlib/tradefed:emulator_test_suite",
        "//testlib/java/com/android/tools/testlib/tradefed:log_saver",
        "//testlib/java/com/android/tools/testlib/tradefed:xml_reporter",
    ],
)
```

All of the host tests are included in two jar files to keep the overall file
count and size down, as common dependencies are merged. We are using a pre-built
tradefed package, which has some older common java libraries with versions we
cannot replicate in bazel. Due to the way java resolves dependencies we need two
separate jar files, once which appears in the class path before tradefed and one
after. Initially try placing your test in the `e2e_tests_post` rule, if you
encounter dependency issues, try `e2e_tests_pre`.

## Advanced Usage

### Browsing Fusion Logs

If ETS is run via go/ab or with RBE, the logs will all be in test fusion. To
start from go/ab click on a build, then the `Test Results` tab and
`android_emulator/release` test identifier.

![ETS AB Start Link](screen/38HB2WZbiFd7WMH.png)

The next page is also the page you will see from the link given when running
with RBE. On this page click the `Invocation Details` tab, then click the
`test_uri` link.

![ETS Invocation Details Link](screen/5ccJXEKGMUq624V.png)

The next page will have all the test results run, which with go/ab will be a
long list. You can use the filter box with `ets:presubmit` to find ets and then
click that link.

![ETS Fusion Start Page](screen/9HR5wXQk3zeD2PQ.png)

After a mere 6 clicks you can see the test results! You will land on the `Tests`
tab, also of interest are the `Target Log` tab, which has what is effectively
the stdout, and the `Artifacts` tab will contain the all the test sequencer and
tradefed output files

![ETS Fusion Tests Tab](screen/8AeGPi9uZjYdva8.png)

![ETS Fusion Target Log Tab](screen/4WP6hopfjienULE.png)

![ETS Fusion Artifacts Tab](screen/5rFHNbLLkiBsXne.png)

### Running With RBE

Running locally will generally be faster than RBE, especially if you are making
incremental changes. However, if you want to ensure your newly written test is
not flaky, RBE can be very useful for running ETS many times. Currently this
only works on linux. From the author's experience running ETS 100 times takes
about 20 minutes. A sample command to do so is below:

```bash
$ prebuilts/bazel/linux-x86_64/bazel test --runs_per_test=100 --config=remote --config=sponge --config=ants @goldfish_test//ets:presubmit

...
(09:03:29) INFO: Build completed successfully, 11533 total actions
@goldfish_test//ets:presubmit                                            PASSED in 702.7s
  Stats over 100 runs: max = 702.7s, min = 352.5s, avg = 458.1s, dev = 45.4s

Executed 1 out of 1 test: 1 test passes.
(09:03:30) INFO: Streaming build results to: https://fusion2.corp.google.com/invocations/ec90d392-e320-489f-87a5-15a502201d0f
```

Opening the link at the bottom of the output will take you to the second page
listed above, after which you can click through to get to the results. Do to the
way bazel configs work, even if you built everything locally first, it will need
to be rebuilt due to the config change.

### Running With an Existing Emulator

Currently the majority of the time for ETS is spent booting the emulator. To
speed things up, you can run against an existing emulator using a different
bazel rule. Note that you must have passed the correct flags to enable GRPC
connections without authentication, the other tests use the `-grpc-allowlist`
flag with the test authentication file.

```bash
$ prebuilts/bazel/linux-x86_64/bazel test @goldfish_test//ets:external_presubmit
```

This works on all platforms (Linux, macOS, and Windows) by scanning for 
emulator discovery files (see `external_ets_cfg.py` in the same 
directory as this file).

Also of note is that the CloseEmulatorTest module is not run, as that would
terminate the existing emulator which is counter productive to the iteration
speed.

### More Advanced Testing {#advanced-code}

#### UI Automator

The best information on more advanced on-device tests is from your favorite
search engine/AI agent. However the
[ScreenshotTest.kt](https://source.corp.google.com/h/googleplex-android/platform/superproject/emu-main-next/+/emu-main-next:third_party/adt-infra/goldfish_test/ets/java/com/android/tools/e2etests/display/ScreenshotTest.kt)
file has some useful examples.

```kotlin
  @Test
  fun screenshotAllFormatsAreEqual() {
    val packageName = "com.google.AnimateBox"
    val device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())
    Log.i(TAG, "Starting animation app")

    // Stop the animation app if it is already running so we start from a clean state.
    adb.shell("am force-stop $packageName")

    val watcher = LogcatWatcher(adb, FILTER)

    device.pressHome()
    val launchIntent = context.getPackageManager().getLaunchIntentForPackage(packageName)
    launchIntent!!.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TASK)
    context.startActivity(launchIntent)

    Assert.assertNotNull(device.wait(Until.hasObject(By.pkg(packageName).depth(0)), 5000))
    ...
  }
```

This code snippet is using the
[UI Automator](https://developer.android.com/training/testing/other-components/ui-automator)
library. At a high level this code stops the package if it is running via adb,
then launches the activity and waits for it. According to the documentation this
process is intuitive. The library can do much more advanced UI interactions,
however this is currently all that ETS offers as an example

#### Advanced Tradefed Config

The config file
[ScreenshotTest.config](https://source.corp.google.com/h/googleplex-android/platform/superproject/emu-main-next/+/emu-main-next:third_party/adt-infra/goldfish_test/ets/java/com/android/tools/e2etests/display/ScreenshotTest.config)
also has some more advanced features:

```xml
<configuration description="Tests related to the emulator screenshots">
    <target_preparer class="com.android.tradefed.targetprep.suite.SuiteApkInstaller">
        <option name="cleanup-apks" value="true" />
        <option name="test-file-name" value="ScreenshotTest.apk" />
        <option name="test-file-name" value="app-debug.apk" />
    </target_preparer>

    <test class="com.android.tradefed.testtype.AndroidJUnitTest" >
        <option name="package" value="com.android.tools.e2etests.display" />
    </test>
    <metrics_collector class="com.android.tradefed.device.metric.FilePullerLogCollector">
        <option name="directory-keys" value="/storage/emulated/0/googletest/test_outputfiles" />
        <option name="collect-on-run-ended-only" value="true" />
    </metrics_collector>
</configuration>
```

Here a second apk is installed, the AnimateBox app-debug.apk. Because this file
is small it is included in the android-ets.zip file. Larger apks, like the
vulkan tests, will be kept separately to avoid bloat.

Screenshots are also pulled from the device using tradefed's
FilePullerLogCollector. To save your own files, use a code like the following:

```kotlin
  val testStorage = PlatformTestStorageRegistry.getInstance()
  testStorage.openOutputFile("foo.txt").use { it.write(myByteArray) }
```

It should be noted that the file name that appears in the output will have a
random string inserted by some layer of tradefed.

#### Passing Options to Tests

It can be useful to pass additional information directly to a test, like the
GRPC port or the path to a dependent APK file. For on-device tests, the
following code can be used:

```kotlin
  val grpcPort = InstrumentationRegistry.getArguments().getString("grpc-port", "0")
```

This value must be passed on the command line to tradefed in the following form:

```bash
  --test-arg com.android.tradefed.testtype.AndroidJUnitTest:instrumentation-arg:grpc-port:=1234
```

This value is currently handled as part of the test sequencer config.

For host side tests the process is a bit different, your kotlin code looks like:

```kotlin
  import com.android.tradefed.config.Option
  ...
  @Option(name = "apk_path", description = "Path to hellovk.apk") private var mApkPath: String = ""
```

With the value passed to tradefed in the following form:

```bash
  --module-arg ModuleName:set-option:apk_path:/path/to/apk
```

For reference the VulkanAppTest was written as a host test under the false
belief that separate applications could not be launched from an on-device test.
It may be migrated to an on-device test in the future.