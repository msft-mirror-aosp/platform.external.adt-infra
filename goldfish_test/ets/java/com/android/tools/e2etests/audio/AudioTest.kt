package com.android.tools.e2etests.audio

import com.android.emulator.v2.GetAudioStateRequest
import com.android.emulator.v2.MicrophoneInput
import com.android.emulator.v2.MicrophoneInputUpdate
import com.android.emulator.v2.SampleFormat
import com.android.emulator.v2.UpdateAudioStateRequest
import com.google.testing.junit.testparameterinjector.TestParameter
import com.google.testing.junit.testparameterinjector.TestParameterInjector
import io.grpc.Status
import kotlin.math.abs
import kotlin.math.max
import org.junit.After
import org.junit.Assert
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/**
 * End-to-end tests of the v2 `AudioService` against a running emulator.
 *
 * The test APK is both the guest app and the gRPC client: it records the guest microphone with
 * `AudioRecord` while injecting a sine wave over gRPC (and plays a tone through `AudioTrack` while
 * capturing the speaker over gRPC), then checks the dominant frequency with an FFT. Matching the
 * frequency proves the audio went through the whole path (format conversion, resampling, virtio-snd
 * and the Android audio stack), not just that bytes arrived.
 */
@RunWith(TestParameterInjector::class)
class AudioTest {

  enum class InjectedFormat(
    val sampleRateHz: Int,
    val channels: Int,
    val format: SampleFormat,
    val freqHz: Double,
  ) {
    // Matches the guest format: no conversion.
    PCM16_48K_MONO_1KHZ(48000, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT, 1000.0),
    // Resampled 44.1 -> 48 kHz and downmixed stereo -> mono from float.
    F32_44K1_STEREO_440HZ(44100, 2, SampleFormat.SAMPLE_FORMAT_F32_BIT, 440.0),
    // Upsampled 16 -> 48 kHz.
    PCM16_16K_MONO_2500HZ(16000, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT, 2500.0),
  }

  /** Formats a client can request from `StreamSpeakerAudio`. */
  enum class SpeakerFormat(val sampleRateHz: Int, val channels: Int, val format: SampleFormat) {
    // The device mixer's native format.
    PCM16_48K_MONO(48000, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT),
    // Float conversion with both channels delivered.
    F32_48K_STEREO(48000, 2, SampleFormat.SAMPLE_FORMAT_F32_BIT),
    // Downsampled for speech pipelines.
    PCM16_16K_MONO(16000, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT),
  }

  @Before
  fun setUp() {
    Guest.allowRecording()
    resetMixer()
  }

  @After
  fun tearDown() {
    resetMixer()
  }

  @Test
  fun hostMicrophoneIsListedAndMutedByDefault() {
    val state = AudioClient.blocking().getAudioState(GetAudioStateRequest.getDefaultInstance())

    Assert.assertTrue("No microphone inputs reported", state.microphoneInputsCount > 0)
    val host = state.getMicrophoneInputs(0)
    Assert.assertEquals("host", host.sourceId)
    Assert.assertEquals(MicrophoneInput.Kind.HOST, host.kind)
    // ETS launches the emulator without -allow-host-audio, so the host mic must stay off.
    Assert.assertTrue("Host microphone must be muted without -allow-host-audio", host.muted)
  }

  @Test
  fun injectedToneReachesGuestMicrophone(@TestParameter case: InjectedFormat) {
    val pcm =
      Tone.pcm(case.freqHz, case.sampleRateHz, case.channels, case.format, durationMs = 2000)

    val recorded =
      MicrophoneStream().use { stream ->
        Guest.record(durationMs = 2500) {
          stream.sendTone(pcm, case.sampleRateHz, case.channels, case.format, "ets-audio")
        }
      }

    assertTone(case.freqHz, Spectrum.analyze(recorded, GUEST_RATE_HZ))
  }

  @Test
  fun injectAudioClipDeliversToneWhileGuestRecords() {
    val freqHz = 1500.0
    val clip =
      Tone.chunk(
        Tone.pcm(freqHz, 48000, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT, durationMs = 1000),
        48000,
        1,
        SampleFormat.SAMPLE_FORMAT_PCM16_BIT,
        "ets-clip",
      )

    var durationMs = 0L
    val recorded =
      Guest.record(durationMs = 2000) {
        durationMs = AudioClient.blocking(seconds = 15).injectAudioClip(clip).durationMs
      }

    Assert.assertEquals(1000.0, durationMs.toDouble(), 20.0)
    assertTone(freqHz, Spectrum.analyze(recorded, GUEST_RATE_HZ))
  }

  @Test
  fun masterMuteSilencesInjectedAudioWithoutEndingTheStream() {
    updateState(UpdateAudioStateRequest.newBuilder().setMicrophoneMuted(true).build())
    val pcm = Tone.pcm(1000.0, 48000, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT, durationMs = 1500)

    MicrophoneStream().use { stream ->
      val recorded =
        Guest.record(durationMs = 1500) {
          stream.sendTone(pcm, 48000, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT, "ets-muted")
        }

      val analysis = Spectrum.analyze(recorded, GUEST_RATE_HZ)
      Assert.assertTrue("Expected silence while muted, got $analysis", analysis.rms < 50.0)
      Assert.assertNull("Muting must not end the stream", stream.error)
    }
  }

  @Test
  fun inputGainScalesInjectedAmplitude() {
    val sourceId = "ets-gain"
    val unity = recordInjectedTone(sourceId, gain = 1.0f)
    val quarter = recordInjectedTone(sourceId, gain = 0.25f)

    assertTone(1000.0, unity)
    assertTone(1000.0, quarter)
    val ratio = quarter.magnitude / unity.magnitude
    Assert.assertEquals(
      "Gain 0.25 should scale the tone (unity=$unity, quarter=$quarter)",
      0.25,
      ratio,
      0.1,
    )
  }

  @Test
  fun guestPlaybackIsCapturedInRequestedFormat(@TestParameter case: SpeakerFormat) {
    val freqHz = 880.0

    var player: Thread? = null
    val channels =
      captureSpeaker(2500, case.sampleRateHz, case.channels, case.format) {
        player = Guest.playTone(freqHz, durationMs = 3000)
      }
    player?.join(10_000)

    Assert.assertEquals(case.channels, channels.size)
    for ((index, samples) in channels.withIndex()) {
      Assert.assertTrue("No speaker audio captured on channel $index", samples.isNotEmpty())
      assertTone(freqHz, Spectrum.analyze(samples, case.sampleRateHz))
    }
  }

  @Test
  fun guestStereoChannelsStaySeparatedInSpeakerCapture() {
    val freqHz = 660.0

    var player: Thread? = null
    val (left, right) =
      captureSpeaker(2500, GUEST_RATE_HZ, 2) {
        player = Guest.playTone(freqHz, durationMs = 3000, leftChannelOnly = true)
      }
    player?.join(10_000)

    val leftTone = Spectrum.analyze(left, GUEST_RATE_HZ)
    val rightTone = Spectrum.analyze(right, GUEST_RATE_HZ)
    assertTone(freqHz, leftTone)
    Assert.assertTrue(
      "Right channel should stay silent (left=$leftTone, right=$rightTone)",
      rightTone.rms < 0.1 * leftTone.rms,
    )
  }

  @Test
  fun streamFormatChangeMidStreamKeepsAudioFlowing() {
    val sourceId = "ets-reconfigure"
    val first = Tone.pcm(1000.0, 48000, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT, durationMs = 1500)
    val second = Tone.pcm(2000.0, 16000, 1, SampleFormat.SAMPLE_FORMAT_F32_BIT, durationMs = 1500)

    val recorded =
      MicrophoneStream().use { stream ->
        Guest.record(durationMs = 4000) {
            stream.sendTone(first, 48000, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT, sourceId)
            // A real client streams in real time; a format change drops audio still buffered in
            // the old format, so let the first part play out before switching.
            Thread.sleep(1400)
            stream.sendTone(second, 16000, 1, SampleFormat.SAMPLE_FORMAT_F32_BIT, sourceId)
          }
          .also { Assert.assertNull("The format change must not end the stream", stream.error) }
      }

    val peaks = Spectrum.windowPeaks(recorded, GUEST_RATE_HZ).map { it.peakHz }
    val firstTone = peaks.indexOfFirst { isNear(it, 1000.0) }
    val secondTone = peaks.indexOfLast { isNear(it, 2000.0) }
    Assert.assertTrue("Never heard the 1 kHz part: $peaks", firstTone >= 0)
    Assert.assertTrue("Never heard the 2 kHz part after it: $peaks", secondTone > firstTone)
  }

  /** A client that crashes and reconnects under the same source_id gets its input back. */
  @Test
  fun droppedClientStreamFreesItsSourceIdForTheReconnectingClient() {
    val pcm = Tone.pcm(1000.0, 48000, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT, durationMs = 2000)
    MicrophoneStream().apply {
      sendTone(
        pcm.copyOfRange(0, 9600),
        48000,
        1,
        SampleFormat.SAMPLE_FORMAT_PCM16_BIT,
        "ets-crashed",
      )
      cancel("simulated client crash")
    }

    // The reconnecting client may race the server noticing the drop; give it a short grace period.
    val deadline = System.currentTimeMillis() + 3000
    var next: MicrophoneStream
    while (true) {
      next = MicrophoneStream()
      next.send(
        Tone.chunk(
          pcm.copyOfRange(0, 1920),
          48000,
          1,
          SampleFormat.SAMPLE_FORMAT_PCM16_BIT,
          "ets-crashed",
        ),
      )
      if (!next.awaitTermination(1)) break
      Assert.assertEquals(Status.Code.ALREADY_EXISTS, MicrophoneStream.statusOf(next.error))
      Assert.assertTrue(
        "The dropped stream still holds source_id ets-crashed",
        System.currentTimeMillis() < deadline,
      )
      Thread.sleep(100)
    }

    val recorded = next.use { stream ->
      Guest.record(durationMs = 2500) {
        stream.sendTone(pcm, 48000, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT, "ets-crashed")
      }
    }
    assertTone(1000.0, Spectrum.analyze(recorded, GUEST_RATE_HZ))
  }

  @Test
  fun audioStateStreamPushesGuestAndInputChanges() {
    val sourceId = "ets-watch"
    AudioStateWatcher().use { watcher ->
      Assert.assertNotNull("No initial AudioState", watcher.await { true })

      val pcm = Tone.pcm(1000.0, 48000, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT, durationMs = 1500)
      MicrophoneStream().use { stream ->
        var active: com.android.emulator.v2.AudioState? = null
        Guest.record(durationMs = 1500) {
          stream.sendTone(pcm, 48000, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT, sourceId)
          active = watcher.await { state ->
            state.microphoneInUseByGuest &&
              state.microphoneInputsList.any { it.sourceId == sourceId }
          }
        }
        Assert.assertNotNull("Never pushed guest recording plus the $sourceId input", active)
      }

      val idle = watcher.await { state ->
        !state.microphoneInUseByGuest && state.microphoneInputsCount == 1
      }
      Assert.assertNotNull("Never pushed the idle state after recording and injection ended", idle)
    }
  }

  @Test
  fun audioStateReportsWhenTheGuestUsesTheMicrophone() {
    Assert.assertFalse(
      "Microphone reported in use before recording",
      AudioClient.blocking()
        .getAudioState(GetAudioStateRequest.getDefaultInstance())
        .microphoneInUseByGuest,
    )

    var seenInUse = false
    Guest.record(durationMs = 1500) { seenInUse = waitForMicrophoneInUse(true) }

    Assert.assertTrue("AudioState never reported the guest microphone in use", seenInUse)
    Assert.assertTrue(
      "AudioState still reports the microphone in use",
      waitForMicrophoneInUse(false),
    )
  }

  /** A person and an agent talking at the same time are both heard by the guest. */
  @Test
  fun concurrentStreamsFromAPersonAndAnAgentAreMixed() {
    val format = SampleFormat.SAMPLE_FORMAT_PCM16_BIT
    val person = Tone.pcm(1000.0, 48000, 1, format, durationMs = 2000, amplitude = 0.3)
    val agent = Tone.pcm(2500.0, 48000, 1, format, durationMs = 2000, amplitude = 0.3)

    val recorded =
      MicrophoneStream().use { personStream ->
        MicrophoneStream().use { agentStream ->
          Guest.record(durationMs = 2500) {
            personStream.sendTone(person, 48000, 1, format, "ets-person")
            agentStream.sendTone(agent, 48000, 1, format, "ets-agent")
          }
        }
      }

    val personPower = Spectrum.powerAt(recorded, GUEST_RATE_HZ, 1000.0)
    val agentPower = Spectrum.powerAt(recorded, GUEST_RATE_HZ, 2500.0)
    val offTonePower = Spectrum.powerAt(recorded, GUEST_RATE_HZ, 1700.0)
    Assert.assertTrue(
      "The person's tone is missing: $personPower vs $offTonePower",
      personPower > 100 * offTonePower,
    )
    Assert.assertTrue(
      "The agent's tone is missing: $agentPower vs $offTonePower",
      agentPower > 100 * offTonePower,
    )
  }

  @Test
  fun streamReusingALiveSourceIdIsRejectedWithAlreadyExists() {
    val pcm = Tone.pcm(1000.0, 48000, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT, durationMs = 20)
    MicrophoneStream().use { first ->
      first.sendTone(pcm, 48000, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT, "ets-测试_🚀_é")
      Assert.assertTrue("Mixer input never appeared", waitForInput("ets-测试_🚀_é"))

      MicrophoneStream().use { second ->
        second.sendTone(pcm, 48000, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT, "ets-测试_🚀_é")
        Assert.assertTrue("Duplicate stream was not rejected", second.awaitTermination(10))
        Assert.assertEquals(Status.Code.ALREADY_EXISTS, MicrophoneStream.statusOf(second.error))
      }
      Assert.assertNull("The first stream must survive the rejected one", first.error)
    }
  }

  // --- helpers -------------------------------------------------------------------------------

  /** Injects a 1 kHz tone, applies [gain] to its mixer input, and analyzes what the guest heard. */
  private fun recordInjectedTone(sourceId: String, gain: Float): ToneAnalysis {
    val pcm = Tone.pcm(1000.0, 48000, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT, durationMs = 2000)
    return MicrophoneStream().use { stream ->
      // The mixer input takes this source_id once the server has processed the first chunk.
      stream.send(
        Tone.chunk(
          pcm.copyOfRange(0, 1920),
          48000,
          1,
          SampleFormat.SAMPLE_FORMAT_PCM16_BIT,
          sourceId,
        ),
      )
      Assert.assertTrue("Mixer input $sourceId never appeared", waitForInput(sourceId))
      updateState(
        UpdateAudioStateRequest.newBuilder()
          .addMicrophoneInputs(
            MicrophoneInputUpdate.newBuilder().setSourceId(sourceId).setGain(gain),
          )
          .build(),
      )
      val recorded =
        Guest.record(durationMs = 2500) {
          stream.sendTone(pcm, 48000, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT, sourceId)
        }
      Spectrum.analyze(recorded, GUEST_RATE_HZ)
    }
  }

  private fun assertTone(expectedHz: Double, analysis: ToneAnalysis) {
    val toleranceHz = max(3 * Spectrum.binHz(GUEST_RATE_HZ), expectedHz * 0.01)
    Assert.assertTrue(
      "Expected a ${expectedHz} Hz tone, got $analysis",
      abs(analysis.peakHz - expectedHz) <= toleranceHz,
    )
    Assert.assertTrue("Tone is buried in noise: $analysis", analysis.snrDb > 20.0)
  }

  private fun isNear(hz: Double, expectedHz: Double): Boolean =
    abs(hz - expectedHz) <= max(3 * Spectrum.binHz(GUEST_RATE_HZ), expectedHz * 0.01)

  private fun waitForMicrophoneInUse(expected: Boolean, timeoutMs: Long = 5000): Boolean {
    val deadline = System.currentTimeMillis() + timeoutMs
    while (System.currentTimeMillis() < deadline) {
      val inUse =
        AudioClient.blocking()
          .getAudioState(GetAudioStateRequest.getDefaultInstance())
          .microphoneInUseByGuest
      if (inUse == expected) return true
      Thread.sleep(100)
    }
    return false
  }

  private fun waitForInput(sourceId: String, timeoutMs: Long = 5000): Boolean {
    val deadline = System.currentTimeMillis() + timeoutMs
    while (System.currentTimeMillis() < deadline) {
      val state = AudioClient.blocking().getAudioState(GetAudioStateRequest.getDefaultInstance())
      if (state.microphoneInputsList.any { it.sourceId == sourceId }) return true
      Thread.sleep(50)
    }
    return false
  }

  private fun updateState(request: UpdateAudioStateRequest) {
    AudioClient.blocking().updateAudioState(request)
  }

  private fun resetMixer() {
    updateState(UpdateAudioStateRequest.newBuilder().setMicrophoneMuted(false).build())
  }
}
