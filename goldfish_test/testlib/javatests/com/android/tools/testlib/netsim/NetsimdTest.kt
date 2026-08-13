package com.android.tools.testlib.netsim

import org.junit.Assert
import org.junit.Rule
import org.junit.Test

data class TestCase(val osName: String, val want: String)

class NetsimdTest {

  @Test
  fun testNetsimdProcessName() {
    val cases =
      arrayOf(
        TestCase("Linux", "netsimd"),
        TestCase("Mac", "netsimd"),
        TestCase("Windows", "netsimd.exe"),
        TestCase("Unknown", "netsimd"),
      )

    for (c in cases) {
      val got = netsimdProcessName(c.osName)
      Assert.assertEquals(got, c.want)
    }
  }
}
