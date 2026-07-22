package com.android.tools.testlib.emu

import java.io.BufferedReader
import java.io.OutputStream
import java.util.concurrent.TimeoutException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeoutOrNull
import org.apache.commons.net.telnet.TelnetClient

val TIMEOUT_MS = 5000L

/**
 * Reads a line from the input, with a timeout.
 *
 * @param input The input to read from.
 * @param close The function to call if the timeout is reached. This must close the input stream to
 *   unblock the coroutine.
 * @param timeout The timeout in milliseconds.
 * @return The line read from the input.
 */
fun readLine(input: BufferedReader, close: () -> Unit, timeout: Long = TIMEOUT_MS): String {
  var result: String? = null
  runBlocking {
    val channel = Channel<String>(Channel.UNLIMITED)
    launch(Dispatchers.IO) {
      val line = input.readLine()
      if (line != null) {
         channel.send(line)
      }
    }
    result = withTimeoutOrNull(timeout) { channel.receive() }
    // If the timeout is reached, we must close the connection to unblock the other coroutine.
    if (result == null) {
      close()
    }
  }
  if (result != null) {
    return result
  }
  throw TimeoutException("Timeout waiting for line")
}

/**
 * Handles common Telnet operations for emulator tests.
 *
 * @property
 */
class Telnet(val input: BufferedReader, val output: OutputStream, val disconnect: () -> Unit) {
  companion object {
    fun connect(port: Int): Telnet {
      val tc = TelnetClient()
      tc.connect("localhost", port)
      return Telnet(tc.getInputStream().bufferedReader(), tc.getOutputStream(), { tc.disconnect() })
    }
  }

  /**
   * Returns all lines until "OK" is received.
   *
   * If "KO" is received, throws a TelnetException.
   *
   * @return the list of lines received.
   */
  fun readUntilOk(): List<String> {
    return buildList {
      while (true) {
        val line = readLine(input, disconnect)
        if (line.trim().equals("OK")) {
          break
        }
        if (line.trim().startsWith("KO")) {
          throw TelnetException(line.trim())
        }
        add(line)
      }
    }
  }

  /**
   * Sends a command to the emulator, returning the new lines.
   *
   * If "KO" is received, throws a TelnetException.
   *
   * @return the list of lines received.
   */
  fun sendCommand(command: String): List<String> {
    output.write("$command\n".toByteArray())
    output.flush()
    return readUntilOk()
  }
}

class TelnetException(message: String) : Exception(message)
