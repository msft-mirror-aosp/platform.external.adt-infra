package com.android.tools.e2etests.display

import com.android.tradefed.result.FileInputStreamSource
import com.android.tradefed.result.LogDataType
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner.TestLogData
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import java.nio.file.Files
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import org.junit.Assert
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(DeviceJUnit4ClassRunner::class)
public class AdbScreenCapTest : BaseHostJUnit4Test() {

  @get:Rule public var mLogs: TestLogData = TestLogData()

  @Test
  fun screencapCreatesPngFile() {
    val ts = timestamp()
    val fileName = "/data/local/tmp/__screenshot_${ts}.png"
    getDevice().executeShellCommand("rm ${fileName}")

    getDevice().executeShellCommand("screencap ${fileName}")
    val stdout = getDevice().executeShellCommand("[ -f ${fileName} ] && echo yes")
    Assert.assertTrue(stdout.contains("yes"))

    val tmpImage = getDevice().pullFile(fileName)
    mLogs.addTestLog("screencapCreatesPngFile", LogDataType.PNG, FileInputStreamSource(tmpImage))

    val mimeType = Files.probeContentType(tmpImage.toPath())
    Assert.assertEquals(mimeType, "image/png")
  }
}

fun timestamp(): String {
  val formatter = java.time.format.DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss")
  return java.time.LocalDateTime.now().format(formatter)
}
