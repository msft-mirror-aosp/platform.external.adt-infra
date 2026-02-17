package com.android.tools.testlib.netsim

import java.nio.file.Path
import java.nio.file.Paths
import java.util.HashMap
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

data class TestCase(val osName: String, val want: Path)

class GrpcTest {
  @Rule
  @JvmField
  val tempFolder = TemporaryFolder()

  @Test
  fun testNetsimIniPath() {
    val env = mapOf("XDG_RUNTIME_DIR" to "linux", "HOME" to "mac", "LOCALAPPDATA" to "win")
    val cases = arrayOf(TestCase("Linux", Paths.get("linux", "netsim.ini")),
                        TestCase("Mac", Paths.get("mac", "Library", "Caches", "TemporaryItems", "netsim.ini")),
                        TestCase("Windows", Paths.get("win", "Temp", "netsim.ini")),
                        TestCase("Unknown", Paths.get("/tmp", "netsim.ini")))

    for (c in cases) {
      val got = netsimIniPath(env, c.osName)
      assertEquals(got, c.want)
    }
  }

  @Test
  fun testGetGrpcPort() {
    val tmpDir = tempFolder.getRoot().toString()
    val want = "5678"
    val env = mapOf("XDG_RUNTIME_DIR" to tmpDir, "HOME" to tmpDir, "LOCALAPPDATA" to tmpDir)

    val paths = arrayOf(Paths.get(tmpDir), Paths.get(tmpDir, "Library", "Caches", "TemporaryItems"),
                        Paths.get(tmpDir, "Temp"))

    for (p in paths) {
      createNetsimIni(p, want)
    }

    val got = getGrpcPort(env)
    assertEquals(got, want)
  }
}

private fun createNetsimIni(path: Path, port: String) {
  path.toFile().mkdirs()
  val iniFile = path.resolve("netsim.ini").toFile()
  iniFile.writeText("grpc.port=$port\n")
}
