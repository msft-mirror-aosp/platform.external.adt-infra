/*
 * Copyright (C) 2026 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.android.tools.e2etests.recording

import com.android.emulation.control.incubating.RecordingInfo
import com.android.emulation.control.incubating.ScreenRecordingGrpc
import com.android.tools.e2etests.grpc.getHostGrpcChannel
import com.android.tools.testlib.emu.Discovery
import com.android.tools.testlib.emu.Telnet
import com.android.tools.testlib.emu.eventually
import com.android.tools.testlib.emu.findEmulator
import com.android.tradefed.log.LogUtil.CLog
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import com.google.protobuf.Empty
import io.grpc.ManagedChannel
import io.grpc.Status
import io.grpc.StatusRuntimeException
import io.grpc.stub.StreamObserver
import java.io.File
import java.io.FileInputStream
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit
import org.junit.After
import org.junit.Assert
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import org.junit.runner.RunWith

private const val TAG = "RecordingTest"
private const val ANIMATE_BOX_PACKAGE = "com.google.AnimateBox"
private const val ANIMATE_BOX_ACTIVITY = "com.google.AnimateBox/com.google.emu.MainActivity"
private const val MIN_RECORDED_VIDEO_BYTES = 10240L
private val WEBM_HEADER =
  byteArrayOf(0x1A.toByte(), 0x45.toByte(), 0xDF.toByte(), 0xA3.toByte())

@RunWith(DeviceJUnit4ClassRunner::class)
public class RecordingTest : BaseHostJUnit4Test() {

  @get:Rule public val tmpFolder = TemporaryFolder()

  lateinit var discovery: Discovery
  lateinit var channel: ManagedChannel
  lateinit var screenService: ScreenRecordingGrpc.ScreenRecordingBlockingStub
  lateinit var asyncScreenService: ScreenRecordingGrpc.ScreenRecordingStub
  private var telnet: Telnet? = null
  private var lastStartedRecording: RecordingInfo? = null

  @Before
  fun setUp() {
    discovery = findEmulator(device.getSerialNumber())!!
    channel = getHostGrpcChannel(discovery)
    screenService = ScreenRecordingGrpc.newBlockingStub(channel)
    asyncScreenService = ScreenRecordingGrpc.newStub(channel)
    stopActiveRecordings()
  }

  @After
  fun tearDown() {
    stopActiveRecordings()
    runCatching { device.executeShellCommand("am force-stop $ANIMATE_BOX_PACKAGE") }
    runCatching { telnet?.disconnect() }
    telnet = null
    runCatching {
      channel.shutdown().awaitTermination(5, TimeUnit.SECONDS)
      if (!channel.isTerminated) {
        channel.shutdownNow()
      }
    }
  }

  @Test
  fun screenRecordSendsEvent() {
    val sampleWebm = File(tmpFolder.root, "sample.webm").canonicalFile
    val info =
      RecordingInfo.newBuilder()
        .setWidth(120)
        .setHeight(120)
        .setFileName(sampleWebm.path)
        .build()

    val observedFiles = ConcurrentHashMap.newKeySet<String>()
    asyncScreenService.receiveRecordingEvents(
      Empty.getDefaultInstance(),
      object : StreamObserver<RecordingInfo> {
        override fun onNext(value: RecordingInfo) {
          observedFiles.add(value.fileName)
        }

        override fun onError(t: Throwable) {}

        override fun onCompleted() {}
      },
    )

    CLog.i("%s: Starting the recording: %s", TAG, info)
    startRecording(info)

    Assert.assertTrue(
      "Did not receive a notification, even though I started recording",
      eventually(50, 100) {
        if (observedFiles.contains(info.fileName)) {
          return@eventually true
        }
        runCatching {
          val events =
            withDeadline().receiveRecordingEvents(Empty.getDefaultInstance()).asSequence().toList()
          events.any { it.fileName == info.fileName }
        }.getOrDefault(false)
      },
    )
  }

  @Test
  fun screenRecordsVideo() {
    startAnimationApp()
    val sampleWebm = File(tmpFolder.root, "sample.webm").canonicalFile
    val info =
      RecordingInfo.newBuilder()
        .setWidth(120)
        .setHeight(120)
        .setFileName(sampleWebm.path)
        .build()
    CLog.i("%s: Starting the recording: %s", TAG, info)
    startRecording(info)
    Thread.sleep(5000)
    CLog.i("%s: Stopping the recording: %s", TAG, info)
    stopRecording(info)

    // Bump the size to 10240, as an empty webm will be around 4k already.
    Assert.assertTrue(sampleWebm.exists())
    Assert.assertTrue(
      "We should have recorded a series of frames (size=${sampleWebm.length()})",
      sampleWebm.length() > MIN_RECORDED_VIDEO_BYTES,
    )
  }

  @Test
  fun canOnlyRecordOnce() {
    val sampleWebm = File(tmpFolder.root, "sample.webm").canonicalFile
    val info =
      RecordingInfo.newBuilder()
        .setWidth(120)
        .setHeight(120)
        .setFileName(sampleWebm.path)
        .build()
    startRecording(info)

    val exception =
      Assert.assertThrows(StatusRuntimeException::class.java) {
        // Our second record attempt should result in an error.
        startRecording(info)
      }
    val msg = exception.message ?: ""
    Assert.assertTrue(
      "Unexpected error for duplicate StartRecording: $exception",
      msg.contains("The recorder is not in a stopped state") ||
        msg.contains("already in progress") ||
        exception.status.code == Status.Code.ALREADY_EXISTS,
    )
  }

  @Test
  fun screenRecordsVideoInWebm() {
    startAnimationApp()
    val sampleFile = File(tmpFolder.root, "sample.webm").canonicalFile
    recordVideo(sampleFile)
    verifyRecordedFileHeader(sampleFile, WEBM_HEADER)
  }

  @Test
  fun screenRecordsVideoTelnet() {
    startAnimationApp()
    val console = connectAuthenticatedTelnet()
    val sampleFile = File(tmpFolder.root, "sample_record.webm").canonicalFile

    console.sendCommand("screenrecord start ${sampleFile.path}")
    Thread.sleep(5000)
    console.sendCommand("screenrecord stop")

    verifyRecordedFileHeader(sampleFile, WEBM_HEADER)
  }

  @Test
  fun screenRecordingDuration() {
    startAnimationApp()
    val sampleFile = File(tmpFolder.root, "sample.webm").canonicalFile
    val info =
      RecordingInfo.newBuilder()
        .setWidth(120)
        .setHeight(120)
        .setFileName(sampleFile.path)
        .setTimeLimit(5)
        .build()
    CLog.i("%s: Starting the recording: %s", TAG, info)
    startRecording(info)
    // Recording time limit is set to 5 seconds, so should stop after 5 seconds.
    Thread.sleep(10000)
    // Recording can be started again after 180 secs.
    startRecording(info)
    CLog.i("%s: Stopping the recording: %s", TAG, info)
    stopRecording(info)
    verifyRecordedFileHeader(sampleFile, WEBM_HEADER)
  }

  @Test
  fun screenRecordsWithDifferentOrientations() {
    startAnimationApp()
    val console = connectAuthenticatedTelnet()

    fun rotate() {
      // Rotate the emulator clockwise by 90 degrees.
      console.sendCommand("rotate")
      Thread.sleep(7000)
    }

    // Ensure screen recording works in (reverse) landscape mode.
    val landscapeFile = File(tmpFolder.root, "sample_landscape.webm").canonicalFile
    CLog.i("%s: Rotating the emulator to reverse landscape...", TAG)
    rotate()
    recordVideo(landscapeFile, width = 270, height = 480, durationSeconds = 20)
    verifyRecordedFileHeader(landscapeFile, WEBM_HEADER)

    // Ensure a valid recording is produced while the emulator is rotated.
    val landscapePortraitFile =
      File(tmpFolder.root, "sample_landscape_portrait.webm").canonicalFile
    val info =
      RecordingInfo.newBuilder()
        .setWidth(270)
        .setHeight(480)
        .setFileName(landscapePortraitFile.path)
        .build()
    CLog.i("%s: Starting the recording: %s", TAG, info)
    startRecording(info)
    for (angle in listOf(-180, 90, 0)) {
      CLog.i("%s: Rotating the emulator to %d degrees...", TAG, angle)
      rotate()
    }

    CLog.i("%s: Stopping the recording: %s", TAG, info)
    stopRecording(info)

    checkWebm(landscapePortraitFile, WEBM_HEADER)
  }

  private fun withDeadline(
    timeoutSeconds: Long = 10
  ): ScreenRecordingGrpc.ScreenRecordingBlockingStub {
    return screenService.withDeadlineAfter(timeoutSeconds, TimeUnit.SECONDS)
  }

  private fun startRecording(info: RecordingInfo): RecordingInfo {
    val response = withDeadline(5).startRecording(info)
    lastStartedRecording = info
    return response
  }

  private fun stopRecording(info: RecordingInfo): RecordingInfo {
    val response = withDeadline(5).stopRecording(info)
    if (lastStartedRecording?.fileName == info.fileName) {
      lastStartedRecording = null
    }
    return response
  }

  private fun stopActiveRecordings() {
    lastStartedRecording?.let { info ->
      runCatching { withDeadline(5).stopRecording(info) }
      lastStartedRecording = null
    }
    runCatching {
      val listResponse = withDeadline(5).listRecordings(RecordingInfo.getDefaultInstance())
      for (info in listResponse.recordingsList) {
        if (info.state == RecordingInfo.RecorderState.RECORDER_STATE_RECORDING) {
          runCatching { withDeadline(5).stopRecording(info) }
        }
      }
    }
    runCatching { withDeadline(5).stopRecording(RecordingInfo.getDefaultInstance()) }
  }

  private fun recordVideo(
    sampleFile: File,
    width: Int = 140,
    height: Int = 140,
    durationSeconds: Long = 2,
  ) {
    val info =
      RecordingInfo.newBuilder()
        .setWidth(width)
        .setHeight(height)
        .setFileName(sampleFile.path)
        .build()
    CLog.i("%s: Starting the recording: %s", TAG, info)
    startRecording(info)
    Thread.sleep(durationSeconds * 1000)
    CLog.i("%s: Stopping the recording: %s", TAG, info)
    stopRecording(info)
  }

  private fun verifyRecordedFileHeader(sampleFile: File, expectedHeader: ByteArray) {
    Assert.assertTrue("Expected recorded file ${sampleFile.path} to exist", sampleFile.exists())
    val header = ByteArray(expectedHeader.size)
    val bytesRead = FileInputStream(sampleFile).use { it.read(header) }
    Assert.assertEquals("Recorded file ${sampleFile.path} is too short", expectedHeader.size, bytesRead)
    Assert.assertArrayEquals(
      "${header.contentToString()} != ${expectedHeader.contentToString()}, the magic header",
      expectedHeader,
      header,
    )
  }

  private fun checkWebm(sampleWebm: File, expectedHeader: ByteArray) {
    Assert.assertTrue("Expected recorded file ${sampleWebm.path} to exist", sampleWebm.exists())
    Assert.assertTrue(
      "We should have recorded a series of frames (size=${sampleWebm.length()})",
      sampleWebm.length() > MIN_RECORDED_VIDEO_BYTES,
    )
    verifyRecordedFileHeader(sampleWebm, expectedHeader)
  }

  private fun startAnimationApp() {
    CLog.i("%s: Starting animation app (%s)", TAG, ANIMATE_BOX_PACKAGE)
    device.executeShellCommand("settings put secure immersive_mode_confirmations confirmed")
    device.executeShellCommand("am force-stop $ANIMATE_BOX_PACKAGE")
    device.executeShellCommand("logcat -c")
    device.executeShellCommand("input keyevent KEYCODE_HOME")
    device.executeShellCommand("am start -W -n $ANIMATE_BOX_ACTIVITY")

    Assert.assertTrue(
      "Timed out waiting for $ANIMATE_BOX_PACKAGE to start",
      eventually(300, 100) {
        val logcat = device.executeShellCommand("logcat -d -s aemu:I")
        logcat.contains("--STARTED--")
      },
    )
  }

  private fun connectAuthenticatedTelnet(): Telnet {
    telnet?.let { return it }
    val port = discovery.discoveryIni["port.serial"]!!.toInt()
    val client = Telnet.connect(port)
    val bannerLines = client.readUntilOk()
    val authPath = bannerLines.last().trim().trim('\'')
    val authKey = File(authPath).readText().trim()
    client.sendCommand("auth $authKey")
    telnet = client
    return client
  }
}
