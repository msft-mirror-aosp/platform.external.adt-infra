from __future__ import absolute_import, division, print_function

from absl import app, flags, logging
from cts_runner import CtsRunner

# List of tests we are going to run. All of them will be invoked as:
# run cts xxx
test_list = [
    "-m CtsCameraTestCases -t android.hardware.camera2.cts.RecordingTest",
    "-m CtsCameraTestCases -t android.hardware.camera2.cts.NativeCameraDeviceTest",

    # Data encryption
    "-m CtsKeystoreTestCases",
    "-m CtsAppSecurityHostTestCases -t android.appsecurity.cts.DirectBootHostTest",

    # Network
    "-m CtsNetTestCases -t android.net.cts.IpSecBaseTest",
    "-m CtsNetTestCases -t android.net.wifi.cts.WifiManagerTest",
    "-m CtsLibcoreTestCases -t libcore.java.net.InetAddressTest",
    "-m CtsLibcoreTestCases -t libcore.javax.net.ServerSocketFactoryTest",

    # Telephony
    "-m CtsTelephonyTestCases",

    # Media
    "-m CtsMediaStressTestCases -t android.mediastress.cts.H264R1080pAacLongPlayerTest",
    "-m CtsMediaTestCases -t android.media.cts.MediaCasTest",
    "-m CtsMediaTestCases -t android.media.cts.DecoderTest",
    "-m CtsMediaTestCases -t android.media.cts.VideoDecoderPerfTest",
    "-m CtsMediaTestCases -t android.media.cts.EncodeDecodeTest",

    # Opengl
    "-m CtsNativeHardwareTestCases",
    "-m CtsOpenGLTestCases",
    "-m CtsSkQPTestCases",
    # (1-2 hours) excluded for now.
    # "-m CtsDeqpTestCases",
]

FLAGS = flags.FLAGS
flags.DEFINE_string("log", "cts-sponge.xml", "path of cts-tradefed executable")
flags.DEFINE_string("cts", "/home/android-build/android-cts/tools/cts-tradefed",
                    "path of cts-tradefed executable")
flags.DEFINE_string("aapt_path",
                    "/home/android-build/Android/sdk/build-tools/28.0.3",
                    "The path of of aapt")
flags.DEFINE_list("tests", test_list, "List of cts tests to execute")


def main(argv):
  del argv  # Unused.
  logging.info("Starting CTS run")

  with open(FLAGS.log, 'wb') as log:
    cts_runner = CtsRunner(FLAGS.cts, FLAGS.aapt_path, log)
    for test in FLAGS.tests:
      cts_runner.run(test)

if __name__ == "__main__":
  app.run(main)
