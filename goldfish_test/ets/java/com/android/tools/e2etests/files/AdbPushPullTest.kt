package com.android.tools.e2etests.files

import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import org.junit.Assert
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(DeviceJUnit4ClassRunner::class)
public class AdbPushPullTest : BaseHostJUnit4Test() {

  @Test
  fun pushAndPullFile() {
    val fileName = "/data/local/tmp/__push_file.txt"
    getDevice().executeShellCommand("rm ${fileName}")

    val contents = makeContents()
    Assert.assertTrue(getDevice().pushString(contents, fileName))
    val stdout = getDevice().executeShellCommand("stat -c %s $fileName")
    Assert.assertEquals(stdout.trim().toInt(), contents.length)

    val got = getDevice().pullFileContents(fileName)
    Assert.assertEquals(got, contents)
  }
}

fun makeContents(): String {
  val b = StringBuilder()
  repeat(100) { b.append("lorem ipsum\n") }
  return b.toString()
}
