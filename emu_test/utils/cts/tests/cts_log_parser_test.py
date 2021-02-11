"""Tests for  cts_suite.cts_test_parser."""



from mock import Mock
from .context import CtsLogParser
from absl.testing import absltest
from absl import flags

FLAGS = flags.FLAGS


class CtsRunnerTest(absltest.TestCase):

  def setUp(self):
    self.parser = CtsLogParser(None)
    self.parser.cts_logger = Mock()

  def tearDown(self):
    pass

  def test_HandlePass(self):
    self.parser.add(
        '06-13 21:52:52 I/ConsoleReporter: [1/14 x86 CtsCameraTestCases emulator-5554] android.hardware.camera2.cts.RecordingTest#testSlowMotionRecording pass'
    )
    self.parser.cts_logger.success.assert_called_with(
        'android.hardware.camera2.cts.RecordingTest#testSlowMotionRecording')

  def test_HandleDone(self):
    self.parser.add(
      'I0613 22:09:19.283898 139627335411520 cts_runner.py:42] 06-13 22:09:19 I/ConsoleReporter: [emulator-5554] x86_64 CtsCameraTestCases completed in 4m 45s. 14 passed, 0 failed, 0 not executed'
    )
    self.parser.cts_logger.done.assert_called_with(14, 0)

  def test_IgnoreNonsense(self):
    self.parser.add(
        '06-13 21:51:56 E/ddms: transfer error: secure_mkdirs failed: Operation not permitted'
    )
    self.parser.flush()
    self.assertEqual(0, self.parser.cts_logger.call_count)

  def test_HandleStart(self):
    self.parser.add(
        '06-13 21:52:52 I/ConsoleReporter: [emulator-5554] Starting x86 CtsCameraTestCases with 14 tests'
    )
    self.parser.cts_logger.start.assert_called_with('CtsCameraTestCases', 14)

  def test_HandlException(self):
    line = ('06-13 21:52:51 I/ModuleListener: [14/14] '
            'android.hardware.camera2.cts.RecordingTest#testVideoSnapshot fail:')
    err = """junit.framework.AssertionFailedError: wait for surface change to 1280x720 timed out
    at junit.framework.Assert.fail(Assert.java:50)
    at junit.framework.Assert.assertTrue(Assert.java:20)
    at android.hardware.camera2.cts.testcases.Camera2SurfaceViewTestCase.updatePreviewSurface(Camera2SurfaceViewTestCase.java:652)
    at android.hardware.camera2.cts.RecordingTest.updatePreviewSurfaceWithVideo(RecordingTest.java:1451)
    at android.hardware.camera2.cts.RecordingTest.videoSnapshotTestByCamera(RecordingTest.java:1302)
    at android.hardware.camera2.cts.RecordingTest.videoSnapshotHelper(RecordingTest.java:1096)
    at android.hardware.camera2.cts.RecordingTest.testVideoSnapshot(RecordingTest.java:278)
    at java.lang.reflect.Method.invoke(Native Method)
    at android.test.InstrumentationTestCase.runMethod(InstrumentationTestCase.java:220)
    at android.test.InstrumentationTestCase.runTest(InstrumentationTestCase.java:205)
    at android.test.ActivityInstrumentationTestCase2.runTest(ActivityInstrumentationTestCase2.java:192)
    at junit.framework.TestCase.runBare(TestCase.java:134)
    at junit.framework.TestResult$1.protect(TestResult.java:115)
    at androidx.test.internal.parser.junit3.AndroidTestResult.runProtected(AndroidTestResult.java:73)
    at junit.framework.TestResult.run(TestResult.java:118)
    at androidx.test.internal.parser.junit3.AndroidTestResult.run(AndroidTestResult.java:51)
    at junit.framework.TestCase.run(TestCase.java:124)
    at androidx.test.internal.parser.junit3.NonLeakyTestSuite$NonLeakyTest.run(NonLeakyTestSuite.java:62)
    at androidx.test.internal.parser.junit3.AndroidTestSuite$2.run(AndroidTestSuite.java:101)
    at java.util.concurrent.Executors$RunnableAdapter.call(Executors.java:458)
    at java.util.concurrent.FutureTask.run(FutureTask.java:266)
    at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1167)
    at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:641)
    at java.lang.Thread.run(Thread.java:764)"""
    self.parser.add(line)
    for line in err.split('\n'):
      self.parser.add(line)
    self.parser.flush()
    self.parser.cts_logger.fail.assert_called_with(
        'android.hardware.camera2.cts.RecordingTest#testVideoSnapshot',
        '\n' + err)


if __name__ == '__main__':
  absltest.main()
