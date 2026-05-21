package com.android.tools.e2etests.wifi

import androidx.test.platform.app.InstrumentationRegistry
import com.android.tools.testlib.emu.Adb
import org.junit.After
import org.junit.Assert
import org.junit.Before
import org.junit.Test

class ConnectivityTest {

  val inst = InstrumentationRegistry.getInstrumentation()
  val adb = Adb(inst.getUiAutomation())
  val ipv4Host = "10.0.2.2"
  val ipv6Host = "fec0::2"

  @Before
  fun enableWifiOnly() {
    adb.shell("svc data disable")
    adb.shell("svc wifi enable")
    adb.shell("cmd wifi connect-network AndroidWifi open")
  }

  @Test
  fun wifiHasConnectivity() {
    var dnsSuccess = false
    for (line in adb.shell("dumpsys connectivity --diag")) {
      if (line.contains("DNS UDP dst") && line.contains("SUCCEEDED")) {
        dnsSuccess = true
        break
      }
    }

    Assert.assertTrue("Unable to connect to dns", dnsSuccess)
  }

  @Test
  fun wifiConnectivityWithoutMobileData() {
    var success = false
    for (line in adb.shell("ping -c 3 $ipv4Host")) {
      if (line.contains("64 bytes from") && line.contains("icmp_seq") && line.contains("ttl")) {
        success = true
        break
      }
    }

    Assert.assertTrue("Failed to ping $ipv4Host", success)
  }

  @Test
  fun wlan0HasIpv4() {
    Assert.assertTrue("wlan0 does not have an IPv4 address", hasIp("4"))
  }

  @Test
  fun wlan0HasIpv6() {
    Assert.assertTrue("wlan0 does not have an IPv6 address", hasIp("6"))
  }

  @Test
  fun wlan0CanPingIpv4() {
    var success = false
    for (line in adb.shell("ping -I wlan0 -c 3 $ipv4Host")) {
      if (line.contains("64 bytes from") && line.contains("icmp_seq") && line.contains("ttl")) {
        success = true
        break
      }
    }
    Assert.assertTrue("Failed to ping $ipv4Host", success)
  }

  @Test
  fun wlan0CanPingIpv6() {
    var success = false
    for (line in adb.shell("ping6 -I wlan0 -c 3 $ipv6Host")) {
      if (line.contains("64 bytes from") && line.contains("icmp_seq") && line.contains("ttl")) {
        success = true
        break
      }
    }
    Assert.assertTrue("Failed to ping $ipv6Host", success)
  }

  @After
  fun enableData() {
    // Some tests disable mobile data, always assure it is re-enabled.
    adb.shell("svc data enable")
  }

  fun hasIp(kind: String): Boolean {
    for (line in adb.shell("ip -$kind addr show wlan0")) {
      if (line.contains("scope")) {
        return true
      }
    }
    return false
  }
}
