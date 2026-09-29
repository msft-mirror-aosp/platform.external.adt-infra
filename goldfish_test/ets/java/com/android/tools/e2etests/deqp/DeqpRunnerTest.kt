package com.android.tools.e2etests.deqp

import com.android.ddmlib.Log.LogLevel
import com.android.tradefed.config.Option
import com.android.tradefed.log.LogUtil.CLog
import com.android.tradefed.result.ByteArrayInputStreamSource
import com.android.tradefed.result.LogDataType
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner.TestLogData
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import com.android.tradefed.util.CommandStatus
import java.io.File
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.concurrent.TimeUnit
import org.junit.Assert
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(DeviceJUnit4ClassRunner::class)
public class DeqpRunnerTest : BaseHostJUnit4Test() {

  @Option(
    name = "caselist_file",
    description = "File name or path of the dEQP test case list file",
  )

  // TODO: add all test cases and provide a way to run full dEQP with ETS
  private var mCaselistFile: String = "presubmit.txt"

  @Option(
    name = "timeout",
    description = "Timeout in seconds for each test case run by deqp-runner",
  )
  private var mTimeout: Int = 120

  @get:Rule public var mLogs: TestLogData = TestLogData()

  companion object {
    private const val DEVICE_BASE_DIR = "/data/local/tmp/CtsDeqpTestCases"
    private const val DEVICE_CASELIST_DIR = "$DEVICE_BASE_DIR/caselist"
    private const val DEVICE_TEST_OUT_DIR = "$DEVICE_BASE_DIR/test_out"
    private val KNOWN_STATUSES =
      listOf("Pass", "Fail", "Crash", "Timeout", "Skip", "Incomplete", "Missing")
    private val FAILING_STATUSES = setOf("Fail", "Crash", "Timeout", "Incomplete", "Missing")
    private val TIME_FORMATTER =
      DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss").withZone(ZoneId.systemDefault())
  }

  private fun resolveTestFile(fileName: String): File {
    val direct = File(fileName)
    if (direct.exists() && direct.isFile) {
      return direct
    }

    val baseName = direct.name
    try {
      val depFile = testInformation?.getDependencyFile(baseName, false)
      if (depFile != null && depFile.exists()) {
        return depFile
      }
    } catch (_: Exception) {
      // Fall through to relative paths if not found via testInformation.
    }

    val candidates =
      listOf(
        File("testcases", fileName),
        File("testcases", baseName),
        File("android-ets/testcases", fileName),
        File("android-ets/testcases", baseName),
        File("ets/java/com/android/tools/e2etests/deqp", fileName),
        File("ets/java/com/android/tools/e2etests/deqp/testcases", baseName),
      )
    for (candidate in candidates) {
      if (candidate.exists() && candidate.isFile) {
        return candidate
      }
    }
    return File("testcases", baseName)
  }

  private fun resolveCtsDeqpDir(anchorFile: File): File {
    val candidates = mutableListOf<File>()
    anchorFile.parentFile?.let { parent ->
      candidates.add(File(parent, "CtsDeqpTestCases"))
      parent.parentFile?.let { grandParent ->
        candidates.add(File(grandParent, "CtsDeqpTestCases"))
      }
    }
    candidates.addAll(
      listOf(
        File("CtsDeqpTestCases"),
        File("testcases/CtsDeqpTestCases"),
        File("android-ets/testcases/CtsDeqpTestCases"),
        File("ets/java/com/android/tools/e2etests/deqp/CtsDeqpTestCases"),
      )
    )
    for (candidate in candidates) {
      if (candidate.exists() && candidate.isDirectory) {
        return candidate
      }
    }
    return File(anchorFile.parentFile ?: File("testcases"), "CtsDeqpTestCases")
  }

  private fun pushCtsDataDirs(dev: com.android.tradefed.device.ITestDevice, ctsDir: File) {
    val subDirs =
      ctsDir.listFiles()?.filter { it.isDirectory }?.sortedBy { it.name } ?: emptyList()
    if (subDirs.isEmpty()) {
      return
    }

    // Try fast tar-based transfer of all data subdirectories first, with fallback to pushDir
    var tarTransferred = false
    val tempTar = File.createTempFile("cts_deqp_assets_", ".tar")
    try {
      val tarCmd = mutableListOf("tar", "-cf", tempTar.absolutePath, "-C", ctsDir.absolutePath)
      tarCmd.addAll(subDirs.map { it.name })
      val proc = ProcessBuilder(tarCmd).start()
      if (proc.waitFor(60, TimeUnit.SECONDS) && proc.exitValue() == 0 && tempTar.exists()) {
        val remoteTar = "$DEVICE_BASE_DIR/cts_deqp_assets.tar"
        if (dev.pushFile(tempTar, remoteTar)) {
          val untarRes =
            dev.executeShellV2Command(
              "tar -xf $remoteTar -C $DEVICE_BASE_DIR && rm -f $remoteTar",
              120L,
              TimeUnit.SECONDS,
              0,
            )
          if (untarRes.status == CommandStatus.SUCCESS && untarRes.exitCode == 0) {
            tarTransferred = true
          }
        }
      }
    } catch (e: Exception) {
      CLog.logAndDisplay(LogLevel.WARN, "Fast tar transfer failed, falling back to pushDir: $e")
    } finally {
      tempTar.delete()
    }

    if (!tarTransferred) {
      for (subDir in subDirs) {
        val remoteSubDir = "$DEVICE_BASE_DIR/${subDir.name}"
        dev.executeShellCommand("mkdir -p $remoteSubDir")
        Assert.assertTrue(
          "Failed to push directory ${subDir.absolutePath} to $remoteSubDir",
          dev.pushDir(subDir, remoteSubDir),
        )
      }
    }
  }

  private fun addTextLog(name: String, content: String) {
    if (content.isNotEmpty()) {
      mLogs.addTestLog(
        name,
        LogDataType.TEXT,
        ByteArrayInputStreamSource(content.toByteArray(Charsets.UTF_8)),
      )
    }
  }

  @Test
  fun testRunDeqp() {
    val dev = getDevice()
    Assert.assertNotNull("Test device must not be null", dev)

    val startInstant = Instant.now()
    val startTimeStr = TIME_FORMATTER.format(startInstant)

    val abi = dev.executeShellCommand("getprop ro.product.cpu.abi").trim()
    val isArm64 = abi.contains("arm64") || abi.contains("aarch64")
    val deqpRunnerLocalName = if (isArm64) "deqp-runner-aarch64" else "deqp-runner"
    val deqpBinaryName = if (isArm64) "deqp-binary64-aarch64" else "deqp-binary64"

    val deqpRunnerFile = resolveTestFile(deqpRunnerLocalName)
    val ctsDeqpDir = resolveCtsDeqpDir(deqpRunnerFile)
    val deqpBinaryFile =
      File(ctsDeqpDir, deqpBinaryName).let {
        if (it.exists()) it else resolveTestFile("CtsDeqpTestCases/$deqpBinaryName")
      }
    val caselistFile = resolveTestFile(mCaselistFile)

    Assert.assertTrue(
      "Local deqp-runner binary not found at ${deqpRunnerFile.absolutePath}",
      deqpRunnerFile.exists(),
    )
    Assert.assertTrue(
      "Local CtsDeqpTestCases directory not found at ${ctsDeqpDir.absolutePath}",
      ctsDeqpDir.exists() && ctsDeqpDir.isDirectory,
    )
    Assert.assertTrue(
      "Local deqp binary not found at ${deqpBinaryFile.absolutePath}",
      deqpBinaryFile.exists(),
    )
    Assert.assertTrue(
      "Local caselist file not found at ${caselistFile.absolutePath}",
      caselistFile.exists(),
    )

    CLog.logAndDisplay(
      LogLevel.INFO,
      "Preparing $DEVICE_BASE_DIR on device ${dev.serialNumber} (ABI: $abi)...",
    )
    dev.executeShellCommand("rm -rf $DEVICE_TEST_OUT_DIR")
    dev.executeShellCommand("mkdir -p $DEVICE_CASELIST_DIR")

    // Push CtsDeqpTestCases data directories (gles2, gles3, gles31, internal, skips, vulkan)
    pushCtsDataDirs(dev, ctsDeqpDir)

    val remoteRunnerPath = "$DEVICE_BASE_DIR/deqp-runner"
    val remoteDeqpBinaryPath = "$DEVICE_BASE_DIR/$deqpBinaryName"
    val remoteCaselistPath = "$DEVICE_CASELIST_DIR/${caselistFile.name}"

    val activeCases =
      caselistFile
        .readLines()
        .map { it.trim() }
        .filter { it.isNotEmpty() && !it.startsWith("#") }
    Assert.assertTrue(
      "No active test cases found in ${caselistFile.absolutePath}",
      activeCases.isNotEmpty(),
    )
    val sanitizedCaselist = activeCases.joinToString("\n") + "\n"

    Assert.assertTrue(
      "Failed to push deqp-runner to $remoteRunnerPath",
      dev.pushFile(deqpRunnerFile, remoteRunnerPath),
    )
    Assert.assertTrue(
      "Failed to push $deqpBinaryName to $remoteDeqpBinaryPath",
      dev.pushFile(deqpBinaryFile, remoteDeqpBinaryPath),
    )
    Assert.assertTrue(
      "Failed to push ${caselistFile.name} to $remoteCaselistPath",
      dev.pushString(sanitizedCaselist, remoteCaselistPath),
    )

    dev.executeShellCommand("chmod +x $remoteRunnerPath $remoteDeqpBinaryPath")

    val skipsDir = File(ctsDeqpDir, "skips")
    val skipsArgs =
      skipsDir
        .listFiles()
        ?.filter { it.isFile && it.name.endsWith(".txt") }
        ?.sortedBy { it.name }
        ?.joinToString(" ") { "--skips=./skips/${it.name}" }
        ?: ""
    val skipsFlag = if (skipsArgs.isNotEmpty()) " $skipsArgs" else ""

    val deqpCmd =
      "cd $DEVICE_BASE_DIR && ./deqp-runner run --deqp=./$deqpBinaryName " +
        "--output test_out --timeout $mTimeout --caselist=./caselist/${caselistFile.name}$skipsFlag " +
        "-- --deqp-surface-width=256 --deqp-surface-height=256 " +
        "--deqp-surface-type=pbuffer --deqp-gl-config-name=rgba8888d24s8ms0 " +
        "--deqp-visibility=hidden"

    CLog.logAndDisplay(LogLevel.INFO, "Executing command on device: $deqpCmd")
    val cmdResult =
      dev.executeShellV2Command(deqpCmd, (mTimeout.toLong() * 5).coerceAtLeast(300L), TimeUnit.SECONDS, 0)

    val endInstant = Instant.now()
    val endTimeStr = TIME_FORMATTER.format(endInstant)
    val durationSeconds = (endInstant.toEpochMilli() - startInstant.toEpochMilli()) / 1000.0
    val durationStr = String.format("%.2fs", durationSeconds)

    val runnerStdout = cmdResult.stdout ?: ""
    val runnerStderr = cmdResult.stderr ?: ""
    addTextLog("deqp_runner_stdout", runnerStdout)
    if (runnerStderr.isNotBlank()) {
      addTextLog("deqp_runner_stderr", runnerStderr)
    }

    val resultsCsv = dev.pullFileContents("$DEVICE_TEST_OUT_DIR/results.csv") ?: ""
    val failuresCsv = dev.pullFileContents("$DEVICE_TEST_OUT_DIR/failures.csv") ?: ""
    val deviceInfoLog = dev.pullFileContents("$DEVICE_TEST_OUT_DIR/dEQP-VK.info.device") ?: ""

    addTextLog("deqp_results_csv", resultsCsv)
    addTextLog("deqp_failures_csv", failuresCsv)
    addTextLog("deqp_vk_device_info", deviceInfoLog)

    // Collect any per-chunk failure logs or qpa files generated by deqp-runner
    val extraFailureLogs = StringBuilder()
    val outFilesList =
      dev
        .executeShellCommand("ls -1 $DEVICE_TEST_OUT_DIR 2>/dev/null")
        .lines()
        .map { it.trim() }
        .filter { it.isNotEmpty() }
    for (fileName in outFilesList) {
      if (fileName.endsWith(".log") || fileName.endsWith(".qpa")) {
        val content = dev.pullFileContents("$DEVICE_TEST_OUT_DIR/$fileName") ?: ""
        if (content.isNotEmpty()) {
          addTextLog("deqp_test_out_$fileName", content)
          if (fileName.endsWith(".log")) {
            extraFailureLogs.append("--- $fileName ---\n").append(content).append("\n")
          }
        }
      }
    }

    val totalCounts = KNOWN_STATUSES.associateWith { 0 }.toMutableMap()
    val individualResults = mutableListOf<Triple<String, String, String>>()
    val failingCasesByType = mutableMapOf<String, MutableList<String>>()

    // Parse results.csv (format: test_name,Status,duration)
    for (line in resultsCsv.lines()) {
      val trimmed = line.trim()
      if (trimmed.isEmpty()) continue
      val parts = trimmed.split(",")
      if (parts.size >= 2) {
        val testName = parts[0].trim()
        val rawStatus = parts[1].trim()
        val testDur = if (parts.size >= 3) parts[2].trim() else ""
        val statusTitle =
          rawStatus.lowercase().replaceFirstChar { it.titlecase() }
        individualResults.add(Triple(testName, statusTitle, testDur))
        totalCounts[statusTitle] = (totalCounts[statusTitle] ?: 0) + 1
        if (statusTitle in FAILING_STATUSES) {
          failingCasesByType.getOrPut(statusTitle) { mutableListOf() }.add(testName)
        }
      }
    }

    // Also parse failures.csv in case any failure wasn't captured in results.csv
    for (line in failuresCsv.lines()) {
      val trimmed = line.trim()
      if (trimmed.isEmpty()) continue
      val parts = trimmed.split(",")
      if (parts.size >= 2) {
        val testName = parts[0].trim()
        val statusTitle = parts[1].trim().lowercase().replaceFirstChar { it.titlecase() }
        if (statusTitle in FAILING_STATUSES) {
          val list = failingCasesByType.getOrPut(statusTitle) { mutableListOf() }
          if (testName !in list) {
            list.add(testName)
          }
        }
      }
    }

    // Build comprehensive test summary report matching emu_mesa_deqp_runner
    val summary = StringBuilder()
    summary.appendLine("========================================")
    summary.appendLine("         DEQP RUNNER TEST SUMMARY       ")
    summary.appendLine("========================================")
    summary.appendLine(String.format("%-12s: %s", "Start Time", startTimeStr))
    summary.appendLine(String.format("%-12s: %s", "End Time", endTimeStr))
    summary.appendLine(String.format("%-12s: %s", "Duration", durationStr))
    summary.appendLine(String.format("%-12s: %s (ABI: %s)", "Device", dev.serialNumber, abi))
    summary.appendLine(
      String.format(
        "%-12s: %s (exitCode=%s)",
        "Status",
        cmdResult.status,
        cmdResult.exitCode,
      )
    )
    summary.appendLine("----------------------------------------")
    for (status in KNOWN_STATUSES.sorted()) {
      summary.appendLine(String.format("%-12s: %d", status, totalCounts[status] ?: 0))
    }
    summary.appendLine("========================================")
    summary.appendLine()
    summary.appendLine("Command Executed:")
    summary.appendLine("----------------------------------")
    summary.appendLine(deqpCmd)
    summary.appendLine()

    if (deviceInfoLog.isNotBlank()) {
      summary.appendLine("Vulkan Device Info:")
      summary.appendLine("----------------------------------")
      summary.appendLine(deviceInfoLog.trim())
      summary.appendLine()
    }

    summary.appendLine("deqp-runner Output:")
    summary.appendLine("----------------------------------")
    summary.appendLine(runnerStdout.trim())
    if (runnerStderr.isNotBlank()) {
      summary.appendLine("stderr:")
      summary.appendLine(runnerStderr.trim())
    }
    summary.appendLine()

    summary.appendLine("Individual Test Case Results (${individualResults.size} tests):")
    summary.appendLine("----------------------------------")
    for ((testName, status, testDur) in individualResults) {
      val durSuffix = if (testDur.isNotEmpty()) " (${testDur}s)" else ""
      summary.appendLine(String.format("%-60s : %-8s%s", testName, status, durSuffix))
    }
    summary.appendLine()

    summary.appendLine("Detailed Failing/Unexpected Cases:")
    summary.appendLine("----------------------------------")
    if (failingCasesByType.isNotEmpty()) {
      for (statusTitle in failingCasesByType.keys.sorted()) {
        val cases = failingCasesByType[statusTitle]!!.sorted()
        summary.appendLine("$statusTitle (${cases.size} tests):")
        for (testName in cases) {
          summary.appendLine("  $testName")
        }
        summary.appendLine()
      }
      if (extraFailureLogs.isNotEmpty()) {
        summary.appendLine("Failure Logs:")
        summary.appendLine(extraFailureLogs.toString())
      }
    } else {
      summary.appendLine("No failed or unexpected test cases detected.")
    }

    val summaryText = summary.toString()
    addTextLog("deqp_runner_summary", summaryText)
    CLog.logAndDisplay(LogLevel.INFO, "\n$summaryText")

    val passCount = totalCounts["Pass"] ?: 0
    val skipCount = totalCounts["Skip"] ?: 0
    val allFailedTests = failingCasesByType.values.flatten().sorted()
    val totalUnexpected = allFailedTests.size

    Assert.assertEquals(
      "Detected $totalUnexpected unexpected dEQP test failure(s): $allFailedTests\n$summaryText",
      0,
      totalUnexpected,
    )
    Assert.assertEquals(
      "deqp-runner command failed with status ${cmdResult.status} (exitCode=${cmdResult.exitCode}).\n$summaryText",
      CommandStatus.SUCCESS,
      cmdResult.status,
    )
    Assert.assertEquals(
      "deqp-runner exited with non-zero code ${cmdResult.exitCode}.\n$summaryText",
      0,
      cmdResult.exitCode ?: -1,
    )
    Assert.assertTrue(
      "Expected at least 1 passing or skipped dEQP test, but Pass=$passCount, Skip=$skipCount.\n$summaryText",
      passCount + skipCount > 0,
    )
  }
}
