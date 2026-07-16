package com.android.tools.testlib.emu

import java.io.ByteArrayOutputStream
import java.io.Reader
import java.util.concurrent.TimeoutException
import java.util.concurrent.locks.Condition
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock
import org.junit.Assert
import org.junit.Test

class BlockingReader(val rlock: ReentrantLock, val condition: Condition) : Reader() {

  override fun read(cbuf: CharArray, off: Int, len: Int): Int {
    rlock.withLock { condition.await() }
    return -1
  }

  override fun close() {}
}

class TelnetTest {

  @Test
  fun testReadLineSuccess() {
    val input = "foo\nbar\n".reader().buffered()
    Assert.assertEquals("foo", readLine(input, {}))
    Assert.assertEquals("bar", readLine(input, {}))
  }

  @Test
  fun testReadLineTimeout() {
    val lock = ReentrantLock()
    val condition = lock.newCondition()
    val input = BlockingReader(lock, condition)

    Assert.assertThrows(TimeoutException::class.java) {
      readLine(input.buffered(), { lock.withLock { condition.signalAll() } }, 100L)
    }
  }

  @Test
  fun testTelnetReadUntilOkIsOk() {
    val input = "foo\nbar\nOK\n".reader().buffered()
    val output = ByteArrayOutputStream()
    val telnet = Telnet(input, output, {})
    val want = listOf("foo", "bar")
    Assert.assertEquals(want, telnet.readUntilOk())
  }

  @Test
  fun testTelnetReadUntilOkIsKo() {
    val input = "foo\nbar\nKO: error\n".reader().buffered()
    val output = ByteArrayOutputStream()
    val telnet = Telnet(input, output, {})
    Assert.assertThrows(TelnetException::class.java) {
      telnet.readUntilOk()
    }
  }

  @Test
  fun testTelnetSendCommandIsOk() {
    val input = "foo\nbar\nOK\n".reader().buffered()
    val output = ByteArrayOutputStream()
    val telnet = Telnet(input, output, {})
    val want = listOf("foo", "bar")
    Assert.assertEquals(want, telnet.sendCommand("go"))
    Assert.assertEquals("go\n", output.toString())
  }

  @Test
  fun testTelnetSendCommandIsKo() {
    val input = "foo\nbar\nKO: error\n".reader().buffered()
    val output = ByteArrayOutputStream()
    val telnet = Telnet(input, output, {})
    Assert.assertThrows(TelnetException::class.java) {
      telnet.sendCommand("go")
    }
    Assert.assertEquals("go\n", output.toString())
  }

}
