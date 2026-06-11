package com.android.tools.testlib.netsim

import java.nio.file.InvalidPathException
import java.nio.file.Paths
import java.util.logging.Logger
import oshi.SystemInfo

private val logger = Logger.getLogger("Netsimd")

fun netsimdIsLaunched(): Boolean {
  val netsimdName = netsimdProcessName()
  val os = SystemInfo().getOperatingSystem()

  for (proc in os.getProcesses()) {
    val args = proc.getArguments()
    if (args.isEmpty()) {
      continue
    }

    // Log process arguments to help debug failures
    logger.info(
        "Checking process arguments to validate netsim has launched: ${args.joinToString(", ")}"
    )

    val executablePath = args[0]
    try {
      val path = Paths.get(executablePath)
      val fileName = path.fileName?.toString() ?: ""

      if (fileName == netsimdName) {
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
