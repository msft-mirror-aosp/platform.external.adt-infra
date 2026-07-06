package com.android.tools.e2etests.telnet

import com.android.tools.testlib.emu.Discovery
import com.android.tools.testlib.emu.Telnet
import com.android.tools.testlib.emu.findEmulator
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import java.io.File
import org.junit.After
import org.junit.Assert
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

val wantCommandsBeforeAuth = listOf("auth", "avd", "help|h|?", "help-verbose", "ping", "quit|exit")
val wantCommandsAfterAuth =
  listOf(
    "automation",
    "avd",
    "cdma",
    "crash",
    "crash-on-exit",
    "debug",
    "event",
    "finger",
    "fold",
    "geo",
    "grpc",
    "gsm",
    "help|h|?",
    "help-verbose",
    "icebox",
    "kill",
    "multidisplay",
    "network",
    "nodraw",
    "phonenumber",
    "physics",
    "ping",
    "posture",
    "power",
    "proxy",
    "qemu",
    "quit|exit",
    "redir",
    "resize-display",
    "restart",
    "rotate",
    "screenrecord",
    "sensor",
    "sms",
    "unfold",
    "virtualscene-image",
  )

@RunWith(DeviceJUnit4ClassRunner::class)
public class TelnetTest : BaseHostJUnit4Test() {

  lateinit var discovery: Discovery
  lateinit var telnet: Telnet

  @Before
  fun setUp() {
    discovery = findEmulator(device.getSerialNumber())!!
    val port = discovery.discoveryIni["port.serial"]!!
    telnet = Telnet.connect(port.toInt())
  }

  @Test
  fun helpBeforeAuth() {
    telnet.readUntilOk()
    val lines = telnet.sendCommand("help")
    val got = setFrom(lines)
    Assert.assertTrue(got.containsAll(wantCommandsBeforeAuth))
  }

  @Test
  fun helpAfterAuth() {
    var lines = telnet.readUntilOk()
    val path = lines[lines.size - 1].trim().trim('\'')
    val authKey = File(path).readText().trim()
    telnet.sendCommand("auth $authKey")
    lines = telnet.sendCommand("help")
    val got = setFrom(lines)
    Assert.assertTrue(got.containsAll(wantCommandsAfterAuth))
  }

  @After
  fun tearDown() {
    telnet.disconnect()
  }
}

fun setFrom(lines: List<String>): Set<String> {
  val result = mutableSetOf<String>()
  for (line in lines) {
    result.add(line.trim())
  }
  return result
}
