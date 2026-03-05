package com.android.tools.testlib.netsim

import com.android.tradefed.log.Log
import io.grpc.Grpc
import io.grpc.InsecureChannelCredentials
import java.io.File
import java.nio.file.Path
import java.nio.file.Paths
import java.util.concurrent.TimeUnit
import netsim.frontend.FrontendServiceGrpc

val TAG = "NetimGrpc"

/**
 * Singleton for sharing a grpc stub across tests.
 *
 * @property stub the grpc stub.
 */
object NetsimController {
  var stub: FrontendServiceGrpc.FrontendServiceBlockingStub? = null

  init {
    val grpcPort = getGrpcPort()
    Log.i(TAG, "Using grpc port: " + grpcPort)
    val channel =
      Grpc.newChannelBuilder("localhost:" + grpcPort, InsecureChannelCredentials.create()).build()
    stub = FrontendServiceGrpc.newBlockingStub(channel)
  }

  fun defaultDeadline(): FrontendServiceGrpc.FrontendServiceBlockingStub {
    return stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
  }
}

fun getGrpcPort(
  env: Map<String, String> = System.getenv(),
  osName: String = System.getProperty("os.name"),
): String {
  var port = ""
  File(netsimIniPath(env, osName).toString()).forEachLine {
    if (!it.trim().startsWith(";")) {
      val parts = it.split("=", limit = 2)
      if (parts.size == 2 && parts[0].trim() == "grpc.port") {
        port = parts[1].trim()
      }
    }
  }
  return port
}

fun netsimIniPath(env: Map<String, String>, osName: String): Path {
  val tmpDir = env["TMPDIR"]
  if (tmpDir != null) {
    val tmpPath = Paths.get(tmpDir, "netsim.ini")
    if (tmpPath.toFile().exists()) {
      return tmpPath
    }
  }

  var path = Paths.get("/tmp")

  when {
    osName.contains("Linux", ignoreCase = true) -> {
      val runtimeDir = env["XDG_RUNTIME_DIR"]
      if (runtimeDir != null) {
        path = Paths.get(runtimeDir)
      }
    }
    osName.contains("Mac", ignoreCase = true) -> {
      val home = env["HOME"]
      if (home != null) {
        path = Paths.get(home, "Library", "Caches", "TemporaryItems")
      }
    }
    osName.contains("Windows", ignoreCase = true) -> {
      val localAppData = env["LOCALAPPDATA"]
      if (localAppData != null) {
        path = Paths.get(localAppData, "Temp")
      }
    }
  }
  Log.i(TAG, "Using netsim directory: " + path.toString())
  return path.resolve("netsim.ini")
}
