package com.android.tools.e2etests.vulkan

import com.android.tradefed.config.Option
import com.android.tradefed.result.LogDataType
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner.TestLogData
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import java.io.File
import java.lang.Thread
import java.nio.file.Files
import java.util.HashMap
import org.junit.Assert
import org.junit.Assume
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(DeviceJUnit4ClassRunner::class)
public class VulkanAppTest : BaseHostJUnit4Test() {
  @Option(name = "apk_paths", description = "Map of app name to APK path")
  private var mApkPaths: MutableMap<String, String> = HashMap()

  @Option(name = "app_activities", description = "Optional map of app name to activity override")
  private var mAppActivities: MutableMap<String, String> = HashMap()

  @Option(
    name = "app_args",
    description = "Optional map of app name to extra 'am start' flags/intent extras",
  )
  private var mAppArgs: MutableMap<String, String> = HashMap()

  @Option(name = "using_lavapipe", description = "True if the emulator is using Lavapipe")
  private var mUsingLavapipe: Boolean = true

  @get:Rule public var mLogs: TestLogData = TestLogData()

  private fun runVulkanAppTest(
    appKey: String,
    packageName: String,
    activityName: String,
    amStartArgs: String = "",
    requiredAbi: String? = null,
    uninstallAfter: Boolean = true,
    screenshotTag: String = appKey,
  ) {
    val apkPath = mApkPaths[appKey]
    Assert.assertTrue(
      "APK path for '$appKey' was not provided via --module-arg VulkanAppTest:set-option:apk_paths:$appKey=<path>",
      !apkPath.isNullOrEmpty(),
    )

    if (requiredAbi != null) {
      val abiList = getDevice().executeShellCommand("getprop ro.product.cpu.abilist").trim()
      Assume.assumeTrue(
        "Skipping $appKey: device supported ABIs ($abiList) do not include $requiredAbi",
        abiList.contains(requiredAbi),
      )
    }

    // Enable 16KB page-size compatibility mode and suppress system warning dialogs
    getDevice().executeShellCommand("setprop bionic.linker.16kb.app_compat.enabled true")
    getDevice().executeShellCommand("setprop pm.16kb.app_compat.disabled false")
    getDevice().executeShellCommand("setprop debug.wm.disable_deprecated_target_sdk_dialog 1")
    getDevice().executeShellCommand("setprop debug.wm.disable_deprecated_abi_dialog 1")
    getDevice().executeShellCommand("settings put global hide_error_dialogs 1")

    val apkFile = File(apkPath!!)
    if (uninstallAfter || getDevice().getAppPackageInfo(packageName) == null) {
      val installArgs = mutableListOf("-t", "-g")
      if (requiredAbi != null) {
        installArgs.add("--abi")
        installArgs.add(requiredAbi)
      }
      val installResult = getDevice().installPackage(apkFile, true, *installArgs.toTypedArray())
      if (installResult != null) {
        Assert.fail("Failed to install $appKey ($apkPath): $installResult")
      }
    }

    try {
      getDevice().executeShellCommand("am force-stop $packageName")
      getDevice().executeShellCommand("appops set --uid $packageName MANAGE_EXTERNAL_STORAGE allow")

      val resolvedArgs = mAppArgs[appKey] ?: amStartArgs

      // Push external shaders/assets if present alongside the APK (e.g., vulkan_samples)
      val apkDir =
        listOfNotNull(apkFile.parentFile, apkFile.canonicalFile.parentFile).firstOrNull {
          File(it, "shaders").exists()
        }
      if (appKey == "vulkan_samples") {
        Assert.assertNotNull(
          "Expected 'shaders' and 'assets' directories alongside $apkPath in runfiles",
          apkDir,
        )
      }
      if (apkDir != null) {
        val remoteBase = "/sdcard/Android/data/$packageName/files"
        if (!getDevice().doesFileExist("$remoteBase/assets/scenes/sponza/Sponza01.gltf")) {
          pushDirectoryDereferenced(File(apkDir, "shaders"), "$remoteBase/shaders")
          pushDirectoryDereferenced(File(apkDir, "assets/fonts"), "$remoteBase/assets/fonts")
          pushDirectoryDereferenced(File(apkDir, "assets/textures"), "$remoteBase/assets/textures")
          pushDirectoryDereferenced(
            File(apkDir, "assets/scenes/sponza"),
            "$remoteBase/assets/scenes/sponza",
          )
          pushDirectoryDereferenced(File(apkDir, "assets/models"), "$remoteBase/assets/models")
          getDevice().executeShellCommand("chmod -R 777 /sdcard/Android/data/$packageName")
        }
        Assert.assertTrue(
          "Failed to stage Sponza01.gltf to $remoteBase/assets/scenes/sponza/Sponza01.gltf",
          getDevice().doesFileExist("$remoteBase/assets/scenes/sponza/Sponza01.gltf"),
        )
      }

      val resolvedActivity = mAppActivities[appKey] ?: activityName
      val component =
        if (resolvedActivity.contains("/")) {
          resolvedActivity
        } else {
          "$packageName/$resolvedActivity"
        }
      val startCmd = buildString {
        append("am start -W -n ")
        append(component)
        if (resolvedArgs.isNotBlank()) {
          append(" ")
          append(resolvedArgs.trim())
        }
      }

      getDevice().executeShellCommand("logcat -b all -c")
      val startOut = getDevice().executeShellCommand(startCmd)
      if (startOut.contains("Error:") || startOut.contains("Exception")) {
        Assert.fail("Failed to start activity for $packageName ($startCmd):\n$startOut")
      }

      Thread.sleep(8000)

      val crashLog = getDevice().executeShellCommand("logcat -d -b crash")
      val eventsLog = getDevice().executeShellCommand("logcat -d -b events")
      val errorLog =
        getDevice().executeShellCommand("logcat -d -s VulkanSamples:E AndroidRuntime:E DEBUG:F libc:F")

      val amCrashLines =
        eventsLog.lines().filter { it.contains("am_crash") && it.contains(packageName) }

      if (
        crashLog.contains(packageName) ||
          amCrashLines.isNotEmpty() ||
          errorLog.contains("[error] Error Message:") ||
          errorLog.contains("Process: $packageName")
      ) {
        Assert.fail(
          "App $packageName ($screenshotTag) crashed or logged a fatal error during execution:\n" +
            "--- am_crash events ---\n${amCrashLines.joinToString("\n")}\n" +
            "--- Crash buffer ---\n$crashLog\n" +
            "--- Error log ---\n$errorLog"
        )
      }

      val windowDump =
        getDevice().executeShellCommand("dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'")
      if (
        windowDump.contains("Application Error") ||
          windowDump.contains("aerr_") ||
          windowDump.contains("PageSizeMismatchDialog") ||
          windowDump.contains("DeprecatedTargetSdkVersionDialog")
      ) {
        Assert.fail("System error or compatibility warning dialog detected on screen:\n$windowDump")
      }

      val pidOut = getDevice().executeShellCommand("pidof $packageName").trim()
      val psOut = getDevice().executeShellCommand("ps -A")
      Assert.assertTrue(
        "Expected $packageName ($screenshotTag) to be running after launch ($startCmd), but process was not found",
        pidOut.isNotEmpty() || psOut.contains(packageName),
      )

      val streamSource = getDevice().getScreenshot()
      mLogs.addTestLog("${screenshotTag}_screenshot", LogDataType.PNG, streamSource)

      getDevice().executeShellCommand("am force-stop $packageName")
    } finally {
      if (uninstallAfter) {
        getDevice().uninstallPackage(packageName)
      }
    }
  }

  private fun pushDirectoryDereferenced(localDir: File, remoteDirPath: String) {
    if (!localDir.exists()) return
    val tmpDir = Files.createTempDirectory("vks_push_").toFile()
    try {
      localDir.walkTopDown().forEach { file ->
        val relPath = file.relativeTo(localDir).path
        if (relPath.isNotEmpty()) {
          val destFile = File(tmpDir, relPath)
          val realFile = file.canonicalFile
          if (realFile.isDirectory) {
            destFile.mkdirs()
          } else if (realFile.isFile) {
            destFile.parentFile?.mkdirs()
            realFile.copyTo(destFile, overwrite = true)
          }
        }
      }
      getDevice().executeShellCommand("mkdir -p $remoteDirPath")
      getDevice().pushDir(tmpDir, remoteDirPath)
    } finally {
      tmpDir.deleteRecursively()
    }
  }

  private fun runVulkanSampleTest(sampleId: String) {
    runVulkanAppTest(
      appKey = "vulkan_samples",
      packageName = "com.khronos.vulkan_samples",
      activityName = "com.khronos.vulkan_samples.SampleLauncherActivity",
      amStartArgs = "-e sample $sampleId",
      uninstallAfter = false,
      screenshotTag = "vulkan_samples_$sampleId",
    )
  }

  @Test
  fun testRunHelloVk() {
    runVulkanAppTest("hellovk", "com.android.hellovk", "com.android.hellovk.VulkanActivity")
  }

  @Test
  fun testRunGears() {
    runVulkanAppTest(
      "gears",
      "de.saschawillems.vulkanGears",
      "de.saschawillems.vulkanSample.VulkanActivity",
      requiredAbi = "arm64-v8a",
    )
  }

  @Test
  fun testRunGltfViewer() {
    runVulkanAppTest(
      "gltf-viewer",
      "de.saschawillems.vulkanglTFPBR",
      "de.saschawillems.vulkanglTFPBR.VulkanActivity",
    )
  }

  @Test
  fun testRunQrGenerator() {
    runVulkanAppTest(
      "qr-generator",
      "com.emu.qr_vulkan_render",
      "com.emu.qr_vulkan_render.MainActivity",
    )
  }

  @Test
  fun testRunTriangle() {
    runVulkanAppTest(
      "triangle",
      "de.saschawillems.vulkanTriangle",
      "de.saschawillems.vulkanSample.VulkanActivity",
      requiredAbi = "arm64-v8a",
    )
  }

  @Test
  fun testRunVulkanCapsViewer() {
    runVulkanAppTest(
      "vulkancapsviewer",
      "de.saschawillems.vulkancapsviewer",
      "org.qtproject.qt5.android.bindings.QtActivity",
      requiredAbi = "arm64-v8a",
    )
  }

  @Test
  fun testRunVulkanSamplesHelloTriangle() {
    runVulkanSampleTest("hello_triangle")
  }

  @Test
  fun testRunVulkanSamplesHelloTriangle13() {
    runVulkanSampleTest("hello_triangle_1_3")
  }

  @Test
  fun testRunVulkanSamplesTextureLoading() {
    runVulkanSampleTest("texture_loading")
  }

  @Test
  fun testRunVulkanSamplesDynamicUniformBuffers() {
    runVulkanSampleTest("dynamic_uniform_buffers")
  }

  @Test
  fun testRunVulkanSamplesComputeNbody() {
    runVulkanSampleTest("compute_nbody")
  }

  @Test
  fun testRunVulkanSamplesSynchronization2() {
    runVulkanSampleTest("synchronization_2")
  }

  @Test
  fun testRunVulkanSamplesSwapchainImages() {
    runVulkanSampleTest("swapchain_images")
  }

  @Test
  fun testRunVulkanSamplesSubpasses() {
    runVulkanSampleTest("subpasses")
  }

  @Test
  fun vulkanLavapipe() {
    Assume.assumeTrue(mUsingLavapipe)
    val stdout = getDevice().executeShellCommand("cmd gpu vkjson")
    Assert.assertTrue(stdout.contains("llvmpipe"))
  }
}
