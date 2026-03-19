# Emulator Test Suite

The Emulator Test Suite is a set of end to end tests for the goldfish emulator.

## Overview

The tests are triggered by bazel test rules, currently you can run all of the
tests via:

```sh
bazel test @goldfish_test//ets:ets
```

Or just the presubmit tests with:

```sh
bazel test @goldfish_test//ets:presubmit
```

The actual test is a thin python wrapper that uses the
[test sequencer](https://g3doc.corp.google.com/wireless/android/devtools/emulator/tradefed_analysis/test_loop_v2/test_seq/docs/QuickStart.md?cl=head)
toolset to do the following:

- Unzip needed packages (emulator, ETS, etc)
- Create an AVD
- Boot the emulator
- Run ETS
- Upload results

## Test Sequencer Configs

The configurations are a flexible way to define the sequence of steps needed for
running a test. This can include steps like download build artifacts, unzipping
them, buildind AVDs, booting emulators, running tradefed, doing reties, etc.

For bazel based ETS tests, this will typically include unzipping the emulator
and ETS, creating the AVD, booting the emulator and running ETS. One config
will be tied to one bazel rule.

The configs are in the progress of migrating to a py-proto based system to
enable re-use. If you need to adjust an AVD or goldfish flags, contact kmagic@.

## ETS Tests

At the lowest level the tests are Junit test classes that run on the device.
They must be written in kotlin and will have access to the emulators GRPC
interface for device interaction. The tests will by their nature be running on
an already booted device. Below is a snippet from:
[BootTest.kt](java/com/android/tools/e2etests/boot/BootTest.kt)

```kotlin
package com.android.tools.e2etests.boot

import com.android.tools.e2etests.grpc.EmulatorController
import com.google.protobuf.Empty
import org.junit.Assert
import org.junit.Test
import java.util.concurrent.TimeUnit

class BootTest {
    @Test
    fun statusIsBooted() {
      val resp = EmulatorController.defaultDeadline().getStatus(Empty.getDefaultInstance())
      Assert.assertTrue(resp.getBooted())
    }
}
```

Like normal junit tests, annotate the function with `@Test` and it will run as a
test. The EmulatorController class can be used to get a cached grpc stub. Always
use a deadline for any grpc method to ensure the test will not hang.

These classes are then grouped into modules, which build as a single APK.
Modules must contain all homogenous tests, all the tests should be able to run
and pass together. If two tests are related, but one only passes on a phone AVD
and the other only passes on a TV AVD, put them in separate modules.

Each module will need two support files, the android xml manifest and a tradefed
config. [BootTestManifest.xml](java/com/android/tools/e2etests/boot/BootTestManifest.xml)
can be relatively simple as seen below. You must enable the internet permission
to use GRPC.

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.android.tools.e2etests.boot" >
    <application android:usesCleartextTraffic="true">>
       <uses-library android:name="android.test.runner"/>
    </application>
    <uses-permission android:name="android.permission.INTERNET" />
    <instrumentation android:name="androidx.test.runner.AndroidJUnitRunner"
         android:targetPackage="com.android.tools.e2etests.boot"
         android:label="Boot test">
    </instrumentation>
</manifest>
```

The tradefed config is responsible for installing the apk and triggering the
test run. Always set cleanup-apks to true to try to keep things clean between
modules.
[BootTest.config](java/com/android/tools/e2etests/boot/BootTest.config)

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
The [BUILD.bazel](java/com/android/tools/e2etests/boot/BUILD.bazel) file lives
in the same directory and builds the apk as well as the package for inclusion in
the android-ets.zip file.

```BUILD
load("@rules_android//rules:rules.bzl", "android_binary")
load("@rules_kotlin//kotlin:android.bzl", "kt_android_library")

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

Lastly the package needs to be included in the overal android-ets.zip bazel rule
from [BUILD.bazel](BUILD.bazel)
```BUILD
pkg_files(
    name = "ets_modules",
    testonly = True,
    srcs = [
        "//ets/java/com/android/tools/e2etests:module_configs",
        "//ets/java/com/android/tools/e2etests/boot:pkg",
    ],
    # Bazel builds the apks in with read-only permissions, which tradefed does
    # not handle.
    attributes = pkg_attributes(mode = "0644"),
    prefix = "android-ets/testcases",
)

```

In the current setup, every test module is run so inclusion in the zip is all
that is needed to get the tests running.
