package com.android.tools.testlib.netsim

import java.nio.file.Paths
import oshi.SystemInfo

fun netsimdIsLaunched(): Boolean {
  val netsimdName = netsimdProcessName()
  val os = SystemInfo().getOperatingSystem()

  for (proc in os.getProcesses()) {
    val args = proc.getArguments()
    System.out.println(args)
    if (!args.isEmpty() && Paths.get(args.get(0)).getFileName().toString() == netsimdName) {
      return true
    }
  }
  return false
}

fun netsimdProcessName(osName: String = System.getProperty("os.name")): String {
  var ret = "netsimd"
  if (osName.contains("Windows", ignoreCase = true)) {
    ret += ".exe"
  }
  return ret
}
