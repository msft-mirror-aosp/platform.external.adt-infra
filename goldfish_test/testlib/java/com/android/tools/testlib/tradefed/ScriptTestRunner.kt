package com.android.tools.testlib.tradefed

import com.android.ddmlib.Log.LogLevel
import com.android.tradefed.config.Option
import com.android.tradefed.invoker.TestInformation
import com.android.tradefed.log.LogUtil.CLog
import com.android.tradefed.metrics.proto.MetricMeasurement.Metric
import com.android.tradefed.result.ITestInvocationListener
import com.android.tradefed.result.TestDescription
import com.android.tradefed.testtype.IRemoteTest
import java.lang.ProcessBuilder
import java.nio.file.Paths
import java.util.HashMap

class ScriptTestRunner : IRemoteTest {

  @Option(name = "script_args", description = "Arguments for the script")
  private var mScriptArgs: List<String> = mutableListOf()

  override fun run(testInfo: TestInformation, listener: ITestInvocationListener) {
    CLog.logAndDisplay(LogLevel.INFO, "Starting script: $mScriptArgs")
    val startTime = System.currentTimeMillis()
    listener.testRunStarted("ScriptTestRunner", 1)

    val test = TestDescription(Paths.get(mScriptArgs.get(0)).getFileName().toString(), "test")
    listener.testStarted(test)

    val pb = ProcessBuilder(mScriptArgs).inheritIO()
    val env = pb.environment()
    env.put("SERIAL", testInfo.getDevice().getSerialNumber())
    val process = pb.start()
    val exitCode = process.waitFor()

    if (exitCode != 0) {
      listener.testFailed(test, "Script failed with exit code: $exitCode")
    }

    listener.testEnded(test, HashMap<String, Metric>())

    listener.testRunEnded(System.currentTimeMillis() - startTime, HashMap<String, Metric>())
  }
}
