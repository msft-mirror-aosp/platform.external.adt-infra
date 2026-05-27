package com.android.tools.testlib.netsim

import java.nio.file.InvalidPathException
import java.nio.file.Paths
import oshi.SystemInfo

fun netsimdIsLaunched(): Boolean {
  val netsimdName = netsimdProcessName()
  val os = SystemInfo().getOperatingSystem()

  for (proc in os.getProcesses()) {
    val args = proc.getArguments()
    try {
      if (!args.isEmpty() && Paths.get(args.get(0)).getFileName().toString() == netsimdName) {
        return true
      }
    } catch (e: InvalidPathException) {
      // Ignore invalid paths and continue checking the rest of the processes.
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
