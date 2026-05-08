package com.android.tools.e2etests.input

import android.os.ParcelFileDescriptor
import android.util.Log
import androidx.test.platform.app.InstrumentationRegistry
import io.grpc.stub.StreamObserver
import java.util.Collections
import java.util.concurrent.TimeUnit
import org.junit.Assert

/**
 * Observes raw Linux input events from a specific device using `getevent`. It parses the output and
 * notifies registered observers.
 *
 * This is useful for verifying that the emulator is correctly generating low-level hardware events
 * in response to test actions.
 */
class EventObserver private constructor(val streamIndex: Int) {
  private var thread: Thread? = null
  private var running = false
  private val observers = Collections.synchronizedList(mutableListOf<StreamObserver<RawEvent>>())
  private var pfd: ParcelFileDescriptor? = null
  private val readyLatch = java.util.concurrent.CountDownLatch(1)

  companion object {
    /**
     * Creates an EventObserver for the device with the given name. It queries `getevent -p` to find
     * the matching stream index.
     *
     * @param deviceName The name of the device as reported by getevent (e.g., "QEMU Virtio
     *   Keyboard").
     * @throws IllegalArgumentException if the device is not found.
     */
    fun observer(deviceName: String): EventObserver {
      val streamIndex = findStreamIndex(deviceName)
      return EventObserver(streamIndex)
    }

    private fun findStreamIndex(deviceName: String): Int {
      val uiAutomation = InstrumentationRegistry.getInstrumentation().getUiAutomation()
      val pfd = uiAutomation.executeShellCommand("getevent -p")
      val fis = ParcelFileDescriptor.AutoCloseInputStream(pfd)
      val reader = fis.bufferedReader()

      var currentEventPath: String? = null
      try {
        while (true) {
          val line = reader.readLine() ?: break
          if (line.contains("add device")) {
            val parts = line.split(":")
            if (parts.size >= 2) {
              currentEventPath = parts[1].trim()
            }
          } else if (line.contains("name:") && line.contains("\"$deviceName\"")) {
            if (currentEventPath != null) {
              val match = "event(\\d+)".toRegex().find(currentEventPath)
              if (match != null) {
                return match.groupValues[1].toInt()
              }
            }
          }
        }
      } catch (e: Exception) {
        Log.e("EventObserver", "Error finding stream index", e)
      } finally {
        pfd.close()
      }
      throw IllegalArgumentException("Device not found: $deviceName")
    }
  }

  fun subscribe(observer: StreamObserver<RawEvent>): EventObserver {
    observers.add(observer)
    return this
  }

  fun unsubscribe(observer: StreamObserver<RawEvent>): EventObserver {
    observers.remove(observer)
    return this
  }

  /**
   * Starts the background thread that runs `getevent` and reads events. This method blocks until
   * the reader is initialized and ready to receive events.
   */
  fun start() {
    if (running) return
    running = true
    thread = Thread {
      val uiAutomation = InstrumentationRegistry.getInstrumentation().getUiAutomation()
      // Run getevent for the specific device
      pfd = uiAutomation.executeShellCommand("getevent -t /dev/input/event$streamIndex")
      val fis = ParcelFileDescriptor.AutoCloseInputStream(pfd)
      val reader = fis.bufferedReader()

      readyLatch.countDown()

      try {
        while (running) {
          val line = reader.readLine() ?: break
          Log.d("EventObserver", "getevent line: $line")
          val event = parseEvent(line)
          if (event != null) {
            synchronized(observers) { observers.forEach { it.onNext(event) } }
          }
        }
        synchronized(observers) { observers.forEach { it.onCompleted() } }
      } catch (e: Exception) {
        Log.e("EventObserver", "Error reading getevent", e)
        synchronized(observers) { observers.forEach { it.onError(e) } }
      }
    }
    thread?.start()
    try {
      val success = readyLatch.await(TestConstants.DEFAULT_TIMEOUT_SECONDS, TimeUnit.SECONDS)
      if (!success) {
        throw IllegalStateException("EventObserver failed to start within timeout")
      }
    } catch (e: InterruptedException) {
      Log.e("EventObserver", "Interrupted waiting for EventObserver to start", e)
      Thread.currentThread().interrupt()
    }
  }

  fun stop() {
    running = false
    try {
      pfd?.close()
    } catch (e: Exception) {
      Log.e("EventObserver", "Error closing pfd", e)
    }
    thread?.interrupt()
    thread?.join(1000)
  }

  /**
   * Helper method to execute an action and wait for a specific number of events to be received.
   *
   * @param count The number of events to wait for.
   * @param timeoutMs The maximum time to wait in milliseconds.
   * @param filter A predicate to filter which events are counted and collected. Defaults to
   *   ignoring EV_SYN events.
   * @param action The lambda to execute (usually triggering the events).
   * @return The list of captured events.
   */
  fun waitForEvents(
      count: Int,
      timeoutMs: Long,
      filter: (RawEvent) -> Boolean = { it.type != 0 },
      action: () -> Unit,
  ): List<RawEvent> {
    val latch = java.util.concurrent.CountDownLatch(count)
    val events = Collections.synchronizedList(mutableListOf<RawEvent>())

    val observer =
        object : StreamObserver<RawEvent> {
          override fun onNext(value: RawEvent) {
            if (filter(value)) {
              events.add(value)
              latch.countDown()
            }
          }

          override fun onError(t: Throwable?) {}

          override fun onCompleted() {}
        }

    subscribe(observer)
    action()
    latch.await(timeoutMs, TimeUnit.MILLISECONDS)
    unsubscribe(observer)

    return events
  }

  private fun parseEvent(line: String): RawEvent? {
    try {
      // Example line 1: [    2626.380552] /dev/input/event2: 0001 0030 00000001
      // Example line 2: [    2626.380552] 0001 0030 00000001
      val parts = line.split("]")
      if (parts.size < 2) return null

      val timestampStr = parts[0].substring(1).trim()
      val timestamp = timestampStr.toDoubleOrNull() ?: 0.0

      val rest = parts[1].trim()
      val colonIndex = rest.indexOf(":")
      val eventStr =
          if (colonIndex >= 0) {
            rest.substring(colonIndex + 1).trim()
          } else {
            rest
          }

      val eventParts = eventStr.split("\\s+".toRegex())
      if (eventParts.size < 3) return null

      val type = eventParts[0].toLong(16).toInt()
      val code = eventParts[1].toLong(16).toInt()
      val value = eventParts[2].toLong(16).toInt()

      return RawEvent(type, code, value, timestamp)
    } catch (e: Exception) {
      Log.e("EventObserver", "Failed to parse line: $line", e)
      return null
    }
  }
}

data class RawEvent(val type: Int, val code: Int, val value: Int, val timestamp: Double)

/** Asserts that the list contains an event with the specified code and value. */
fun List<RawEvent>.assertContains(code: Int, value: Int, message: String? = null): List<RawEvent> {
  val baseMessage = message ?: "Should contain event with code=$code and value=$value"
  Assert.assertTrue(
      "$baseMessage. Actual events received: $this",
      this.any { it.code == code && it.value == value },
  )
  return this
}

/** Asserts that the list contains an event with the specified code. */
fun List<RawEvent>.assertContains(code: Int, message: String? = null): List<RawEvent> {
  val baseMessage = message ?: "Should contain event with code=$code"
  Assert.assertTrue("$baseMessage. Actual events received: $this", this.any { it.code == code })
  return this
}

/** Asserts that the list has at least the expected number of events. */
fun List<RawEvent>.assertSizeAtLeast(size: Int, message: String? = null): List<RawEvent> {
  val baseMessage = message ?: "Expected at least $size events"
  Assert.assertTrue(
      "$baseMessage. Got ${this.size}. Actual events received: $this",
      this.size >= size,
  )
  return this
}

/** Asserts that the list has exactly the expected number of events. */
fun List<RawEvent>.assertSize(size: Int, message: String? = null): List<RawEvent> {
  val baseMessage = message ?: "Expected exactly $size events"
  Assert.assertEquals("$baseMessage. Actual events received: $this", size, this.size)
  return this
}
