package com.android.tools.e2etests.vulkan

import com.android.tradefed.config.Option
import com.android.tradefed.result.LogDataType
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner.TestLogData
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import java.lang.Thread
import org.junit.Assert
import org.junit.Assume
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(DeviceJUnit4ClassRunner::class)
public class VulkanAppTest : BaseHostJUnit4Test() {
  // TODO(kmagic): Use a map here to specify paths to the other apks.
  @Option(name = "apk_path", description = "Path to hellovk.apk") private var mApkPath: String = ""

  @Option(name = "using_lavapipe", description = "True if the emulator is using Lavapipe") private var mUsingLavapipe: Boolean = true

  private val mPackage = "com.android.hellovk"
  private val mActivity = mPackage + "/com.android.hellovk.VulkanActivity"

  @get:Rule public var mLogs: TestLogData = TestLogData()

  @Test
  fun testRunHelloVk() {
    Assert.assertTrue(mApkPath != "")
    // NOTE: This function will uninstall the apk after the test.
    installPackage(mApkPath)
    getDevice().executeShellCommand("am start -n " + mActivity)
    Thread.sleep(10000)
    val stdout = getDevice().executeShellCommand("ps -A")
    Assert.assertTrue(stdout.contains(mPackage))

    val streamSource = getDevice().getScreenshot()
    mLogs.addTestLog("hellovk_screenshot", LogDataType.PNG, streamSource)
  }

  @Test
  fun vulkanLavapipe() {
    Assume.assumeTrue(mUsingLavapipe)
    val stdout = getDevice().executeShellCommand("cmd gpu vkjson")
    Assert.assertTrue(stdout.contains("llvmpipe"))
  }
}
