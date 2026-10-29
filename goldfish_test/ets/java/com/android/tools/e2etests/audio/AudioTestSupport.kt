package com.android.tools.e2etests.audio

import android.Manifest
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import android.util.Log
import androidx.test.platform.app.InstrumentationRegistry
import com.android.emulator.v2.AudioChunk
import com.android.emulator.v2.AudioServiceGrpc
import com.android.emulator.v2.AudioState
import com.android.emulator.v2.SampleFormat
import com.android.emulator.v2.StreamAudioStateRequest
import com.android.emulator.v2.StreamMicrophoneAudioResponse
import com.android.emulator.v2.StreamSpeakerAudioRequest
import com.android.tools.e2etests.grpc.GrpcChannel
import com.google.protobuf.ByteString
import io.grpc.Status
import io.grpc.stub.ClientCallStreamObserver
import io.grpc.stub.ClientResponseObserver
import io.grpc.stub.StreamObserver
import java.io.ByteArrayOutputStream
import java.io.Closeable
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.CountDownLatch
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import kotlin.concurrent.thread
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.log10
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

const val TAG = "AudioTest"

/** Sample rate used for guest recording and playback. */
const val GUEST_RATE_HZ = 48000

/** v2 AudioService stubs on the shared emulator gRPC channel. */
object AudioClient {
  val blocking: AudioServiceGrpc.AudioServiceBlockingStub by lazy {
    AudioServiceGrpc.newBlockingStub(GrpcChannel.instance)
  }
  val async: AudioServiceGrpc.AudioServiceStub by lazy {
    AudioServiceGrpc.newStub(GrpcChannel.instance)
  }

  fun blocking(seconds: Long = 10): AudioServiceGrpc.AudioServiceBlockingStub =
    blocking.withDeadlineAfter(seconds, TimeUnit.SECONDS)
}

/** Interleaved sine-wave PCM in the formats the AudioService accepts. */
object Tone {
  fun pcm(
    freqHz: Double,
    sampleRateHz: Int,
    channels: Int,
    format: SampleFormat,
    durationMs: Int,
    amplitude: Double = 0.5,
  ): ByteArray {
    val frames = sampleRateHz * durationMs / 1000
    val bytesPerSample = if (format == SampleFormat.SAMPLE_FORMAT_F32_BIT) 4 else 2
    val out = ByteBuffer.allocate(frames * channels * bytesPerSample).order(ByteOrder.LITTLE_ENDIAN)
    for (i in 0 until frames) {
      val v = amplitude * sin(2.0 * PI * freqHz * i / sampleRateHz)
      repeat(channels) {
        if (format == SampleFormat.SAMPLE_FORMAT_F32_BIT) {
          out.putFloat(v.toFloat())
        } else {
          out.putShort((v * Short.MAX_VALUE).toInt().toShort())
        }
      }
    }
    return out.array()
  }

  fun chunk(
    pcm: ByteArray,
    sampleRateHz: Int,
    channels: Int,
    format: SampleFormat,
    sourceId: String? = null,
  ): AudioChunk {
    val builder =
      AudioChunk.newBuilder()
        .setPcmData(ByteString.copyFrom(pcm))
        .setSampleRateHz(sampleRateHz)
        .setChannelCount(channels)
        .setFormat(format)
    if (sourceId != null) {
      builder.setSourceId(sourceId)
    }
    return builder.build()
  }
}

/** Dominant tone of a recording. */
data class ToneAnalysis(
  val peakHz: Double,
  val magnitude: Double,
  val snrDb: Double,
  val rms: Double,
)

/** Hann-windowed radix-2 FFT over the loudest window of a mono recording. */
object Spectrum {
  private const val WINDOW = 8192
  private const val PEAK_HALF_WIDTH = 2

  fun analyze(samples: ShortArray, sampleRateHz: Int): ToneAnalysis =
    analyzeWindow(samples, loudestWindowStart(samples), sampleRateHz)

  /** Dominant tone of every half-overlapping window louder than [minRms], in time order. */
  fun windowPeaks(
    samples: ShortArray,
    sampleRateHz: Int,
    minRms: Double = 500.0,
  ): List<ToneAnalysis> {
    val peaks = mutableListOf<ToneAnalysis>()
    var start = 0
    while (start + WINDOW <= samples.size) {
      val analysis = analyzeWindow(samples, start, sampleRateHz)
      if (analysis.rms >= minRms) peaks.add(analysis)
      start += WINDOW / 2
    }
    return peaks
  }

  private fun analyzeWindow(samples: ShortArray, start: Int, sampleRateHz: Int): ToneAnalysis {
    val re = DoubleArray(WINDOW)
    val im = DoubleArray(WINDOW)
    var sumSquares = 0.0
    for (i in 0 until WINDOW) {
      val s = if (start + i < samples.size) samples[start + i] / 32768.0 else 0.0
      sumSquares += s * s
      re[i] = s * (0.5 - 0.5 * cos(2.0 * PI * i / (WINDOW - 1)))
    }
    fft(re, im)

    val half = WINDOW / 2
    val power = DoubleArray(half) { re[it] * re[it] + im[it] * im[it] }
    var peak = PEAK_HALF_WIDTH + 1
    for (k in peak until half) {
      if (power[k] > power[peak]) peak = k
    }
    var signal = 0.0
    var noise = 0.0
    var noiseBins = 0
    for (k in PEAK_HALF_WIDTH + 1 until half) {
      if (k in (peak - PEAK_HALF_WIDTH)..(peak + PEAK_HALF_WIDTH)) {
        signal += power[k]
      } else {
        noise += power[k]
        noiseBins++
      }
    }
    val meanNoise = max(noise / max(noiseBins, 1), 1e-20)
    return ToneAnalysis(
      peakHz = peak.toDouble() * sampleRateHz / WINDOW,
      magnitude = sqrt(signal),
      snrDb = 10 * log10(signal / ((2 * PEAK_HALF_WIDTH + 1) * meanNoise)),
      rms = sqrt(sumSquares / WINDOW) * 32768.0,
    )
  }

  /** Power of [hz] (Goertzel) over the loudest window of [samples], relative to full scale. */
  fun powerAt(samples: ShortArray, sampleRateHz: Int, hz: Double): Double {
    val start = loudestWindowStart(samples)
    val end = min(start + WINDOW, samples.size)
    val coefficient = 2 * cos(2 * PI * hz / sampleRateHz)
    var previous = 0.0
    var beforePrevious = 0.0
    for (i in start until end) {
      val current = samples[i] / 32768.0 + coefficient * previous - beforePrevious
      beforePrevious = previous
      previous = current
    }
    val n = (end - start).toDouble()
    return (previous * previous + beforePrevious * beforePrevious -
      coefficient * previous * beforePrevious) / (n * n)
  }

  /** Width of one FFT bin. */
  fun binHz(sampleRateHz: Int): Double = sampleRateHz.toDouble() / WINDOW

  private fun loudestWindowStart(samples: ShortArray): Int {
    if (samples.size <= WINDOW) return 0
    var best = 0
    var bestEnergy = -1.0
    var start = 0
    while (start + WINDOW <= samples.size) {
      var energy = 0.0
      for (i in start until start + WINDOW) energy += samples[i].toDouble() * samples[i]
      if (energy > bestEnergy) {
        bestEnergy = energy
        best = start
      }
      start += WINDOW / 4
    }
    return best
  }

  private fun fft(re: DoubleArray, im: DoubleArray) {
    val n = re.size
    var j = 0
    for (i in 1 until n) {
      var bit = n shr 1
      while (j and bit != 0) {
        j = j xor bit
        bit = bit shr 1
      }
      j = j xor bit
      if (i < j) {
        re[i] = re[j].also { re[j] = re[i] }
        im[i] = im[j].also { im[j] = im[i] }
      }
    }
    var len = 2
    while (len <= n) {
      val angle = -2.0 * PI / len
      for (i in 0 until n step len) {
        for (k in 0 until len / 2) {
          val wr = cos(angle * k)
          val wi = sin(angle * k)
          val ur = re[i + k]
          val ui = im[i + k]
          val vr = re[i + k + len / 2] * wr - im[i + k + len / 2] * wi
          val vi = re[i + k + len / 2] * wi + im[i + k + len / 2] * wr
          re[i + k] = ur + vr
          im[i + k] = ui + vi
          re[i + k + len / 2] = ur - vr
          im[i + k + len / 2] = ui - vi
        }
      }
      len = len shl 1
    }
  }
}

/** Guest-side helpers: recording from the microphone and playing to the speaker. */
object Guest {
  private val instrumentation
    get() = InstrumentationRegistry.getInstrumentation()

  /** Lets the instrumentation record audio even though it has no foreground activity. */
  fun allowRecording() {
    val pkg = instrumentation.context.packageName
    instrumentation.uiAutomation.grantRuntimePermission(pkg, Manifest.permission.RECORD_AUDIO)
    shell("appops set $pkg RECORD_AUDIO allow")
  }

  fun shell(command: String): String {
    val pfd = instrumentation.uiAutomation.executeShellCommand(command)
    return android.os.ParcelFileDescriptor.AutoCloseInputStream(pfd).use {
      it.readBytes().toString(Charsets.UTF_8)
    }
  }

  /**
   * Records mono PCM16 from the guest microphone for [durationMs] while [during] runs on the
   * calling thread, and returns the samples.
   */
  fun record(durationMs: Int, during: () -> Unit = {}): ShortArray {
    val format =
      AudioFormat.Builder()
        .setSampleRate(GUEST_RATE_HZ)
        .setChannelMask(AudioFormat.CHANNEL_IN_MONO)
        .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
        .build()
    val minBuffer =
      AudioRecord.getMinBufferSize(
        GUEST_RATE_HZ,
        AudioFormat.CHANNEL_IN_MONO,
        AudioFormat.ENCODING_PCM_16BIT,
      )
    val record =
      AudioRecord.Builder()
        .setAudioSource(unprocessedSourceIfSupported())
        .setAudioFormat(format)
        .setBufferSizeInBytes(max(minBuffer, GUEST_RATE_HZ / 5 * 2))
        .build()
    check(record.state == AudioRecord.STATE_INITIALIZED) { "AudioRecord failed to initialize" }

    val total = GUEST_RATE_HZ * durationMs / 1000
    val samples = ShortArray(total)
    try {
      record.startRecording()
      val reader =
        thread(name = "guest-recorder") {
          var offset = 0
          while (offset < total) {
            val n = record.read(samples, offset, min(1024, total - offset))
            if (n <= 0) break
            offset += n
          }
        }
      during()
      reader.join(durationMs + 5000L)
    } finally {
      record.stop()
      record.release()
    }
    return samples
  }

  /**
   * Plays a sine tone through the guest speaker for [durationMs] on a background thread. With
   * [leftChannelOnly] the track is stereo and the right channel stays silent.
   */
  fun playTone(freqHz: Double, durationMs: Int, leftChannelOnly: Boolean = false): Thread {
    val audioManager = instrumentation.context.getSystemService(AudioManager::class.java)
    audioManager.setStreamVolume(
      AudioManager.STREAM_MUSIC,
      audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC),
      0,
    )
    val mono = Tone.pcm(freqHz, GUEST_RATE_HZ, 1, SampleFormat.SAMPLE_FORMAT_PCM16_BIT, durationMs)
    val pcm = if (leftChannelOnly) leftOnlyStereo(mono) else mono
    val track =
      AudioTrack.Builder()
        .setAudioAttributes(
          AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_MEDIA)
            .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
            .build(),
        )
        .setAudioFormat(
          AudioFormat.Builder()
            .setSampleRate(GUEST_RATE_HZ)
            .setChannelMask(
              if (leftChannelOnly) AudioFormat.CHANNEL_OUT_STEREO else AudioFormat.CHANNEL_OUT_MONO,
            )
            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
            .build(),
        )
        .setTransferMode(AudioTrack.MODE_STREAM)
        .build()
    return thread(name = "guest-player") {
      try {
        track.play()
        track.write(pcm, 0, pcm.size)
        track.stop()
      } finally {
        track.release()
      }
    }
  }

  /** Interleaves mono PCM16 into stereo with silence on the right channel. */
  private fun leftOnlyStereo(mono: ByteArray): ByteArray {
    val out = ByteArray(mono.size * 2)
    for (i in 0 until mono.size / 2) {
      out[4 * i] = mono[2 * i]
      out[4 * i + 1] = mono[2 * i + 1]
    }
    return out
  }

  private fun unprocessedSourceIfSupported(): Int {
    val audioManager = instrumentation.context.getSystemService(AudioManager::class.java)
    val unprocessed =
      audioManager.getProperty(AudioManager.PROPERTY_SUPPORT_AUDIO_SOURCE_UNPROCESSED)
    // VOICE_RECOGNITION is also specified without AGC, so amplitudes stay comparable.
    return if (unprocessed == "true") MediaRecorder.AudioSource.UNPROCESSED
    else MediaRecorder.AudioSource.VOICE_RECOGNITION
  }
}

/** A `StreamMicrophoneAudio` client stream. Close it to stop injecting. */
class MicrophoneStream : Closeable {
  private val done = CountDownLatch(1)
  @Volatile
  var error: Throwable? = null
    private set

  private val requests: ClientCallStreamObserver<AudioChunk> =
    AudioClient.async
      .withDeadlineAfter(60, TimeUnit.SECONDS)
      .streamMicrophoneAudio(
        object : StreamObserver<StreamMicrophoneAudioResponse> {
          override fun onNext(value: StreamMicrophoneAudioResponse) {}

          override fun onError(t: Throwable) {
            error = t
            done.countDown()
          }

          override fun onCompleted() {
            done.countDown()
          }
        },
      ) as ClientCallStreamObserver<AudioChunk>

  fun send(chunk: AudioChunk) = requests.onNext(chunk)

  /** Drops the call without finishing it, the way a crashed or disconnected client would. */
  fun cancel(reason: String) {
    requests.cancel(reason, null)
    done.await(10, TimeUnit.SECONDS)
  }

  /** Sends [pcm] in 20 ms chunks. The server buffers up to 5 s, so no pacing is needed. */
  fun sendTone(
    pcm: ByteArray,
    sampleRateHz: Int,
    channels: Int,
    format: SampleFormat,
    sourceId: String,
  ) {
    val bytesPerFrame = channels * if (format == SampleFormat.SAMPLE_FORMAT_F32_BIT) 4 else 2
    val chunkBytes = sampleRateHz / 50 * bytesPerFrame
    var offset = 0
    while (offset < pcm.size) {
      val end = min(offset + chunkBytes, pcm.size)
      send(Tone.chunk(pcm.copyOfRange(offset, end), sampleRateHz, channels, format, sourceId))
      offset = end
    }
  }

  /** Waits for the server to end the stream (for example with an error). */
  fun awaitTermination(seconds: Long): Boolean = done.await(seconds, TimeUnit.SECONDS)

  override fun close() {
    if (done.count > 0) {
      requests.onCompleted()
    }
    // The server releases the microphone before it finishes the call, so once this returns the
    // next test can start its own stream.
    done.await(10, TimeUnit.SECONDS)
  }

  companion object {
    fun statusOf(t: Throwable?): Status.Code? = t?.let { Status.fromThrowable(it).code }
  }
}

/**
 * Captures [durationMs] of guest speaker output from `StreamSpeakerAudio` in the requested format
 * while [during] runs, and returns one PCM16-scaled array per channel.
 */
fun captureSpeaker(
  durationMs: Int,
  sampleRateHz: Int = GUEST_RATE_HZ,
  channels: Int = 1,
  format: SampleFormat = SampleFormat.SAMPLE_FORMAT_PCM16_BIT,
  during: () -> Unit,
): List<ShortArray> {
  val bytesPerSample = if (format == SampleFormat.SAMPLE_FORMAT_F32_BIT) 4 else 2
  val wantedBytes = sampleRateHz * durationMs / 1000 * channels * bytesPerSample
  val captured = ByteArrayOutputStream()
  val done = CountDownLatch(1)
  val observer =
    object : ClientResponseObserver<StreamSpeakerAudioRequest, AudioChunk> {
      lateinit var call: ClientCallStreamObserver<StreamSpeakerAudioRequest>

      override fun beforeStart(requestStream: ClientCallStreamObserver<StreamSpeakerAudioRequest>) {
        call = requestStream
      }

      override fun onNext(chunk: AudioChunk) {
        check(chunk.sampleRateHz == sampleRateHz && chunk.channelCount == channels) {
          "Speaker chunk has ${chunk.sampleRateHz} Hz x ${chunk.channelCount}, wanted " +
            "$sampleRateHz Hz x $channels"
        }
        chunk.pcmData.writeTo(captured)
        if (captured.size() >= wantedBytes) {
          call.cancel("captured enough audio", null)
          done.countDown()
        }
      }

      override fun onError(t: Throwable) {
        if (Status.fromThrowable(t).code != Status.Code.CANCELLED) {
          Log.w(TAG, "StreamSpeakerAudio failed", t)
        }
        done.countDown()
      }

      override fun onCompleted() {
        done.countDown()
      }
    }
  AudioClient.async
    .withDeadlineAfter(30, TimeUnit.SECONDS)
    .streamSpeakerAudio(
      StreamSpeakerAudioRequest.newBuilder()
        .setSampleRateHz(sampleRateHz)
        .setChannelCount(channels)
        .setFormat(format)
        .build(),
      observer,
    )
  during()
  done.await(durationMs + 10_000L, TimeUnit.MILLISECONDS)

  val buffer = ByteBuffer.wrap(captured.toByteArray()).order(ByteOrder.LITTLE_ENDIAN)
  val frames = buffer.remaining() / (channels * bytesPerSample)
  val out = List(channels) { ShortArray(frames) }
  for (frame in 0 until frames) {
    for (ch in 0 until channels) {
      out[ch][frame] =
        if (format == SampleFormat.SAMPLE_FORMAT_F32_BIT) {
          (buffer.float.coerceIn(-1f, 1f) * Short.MAX_VALUE).toInt().toShort()
        } else {
          buffer.short
        }
    }
  }
  return out
}

/** Subscribes to `StreamAudioState` and lets a test wait for a matching update. */
class AudioStateWatcher : Closeable {
  private val updates = LinkedBlockingQueue<AudioState>()
  private lateinit var call: ClientCallStreamObserver<StreamAudioStateRequest>

  init {
    AudioClient.async
      .withDeadlineAfter(60, TimeUnit.SECONDS)
      .streamAudioState(
        StreamAudioStateRequest.getDefaultInstance(),
        object : ClientResponseObserver<StreamAudioStateRequest, AudioState> {
          override fun beforeStart(
            requestStream: ClientCallStreamObserver<StreamAudioStateRequest>,
          ) {
            call = requestStream
          }

          override fun onNext(value: AudioState) {
            updates.add(value)
          }

          override fun onError(t: Throwable) {}

          override fun onCompleted() {}
        },
      )
  }

  /** Waits up to [timeoutMs] for an update matching [predicate], skipping older ones. */
  fun await(timeoutMs: Long = 5000, predicate: (AudioState) -> Boolean): AudioState? {
    val deadline = System.currentTimeMillis() + timeoutMs
    while (true) {
      val remaining = deadline - System.currentTimeMillis()
      if (remaining <= 0) return null
      val state = updates.poll(remaining, TimeUnit.MILLISECONDS) ?: return null
      if (predicate(state)) return state
    }
  }

  override fun close() {
    call.cancel("test finished", null)
  }
}
