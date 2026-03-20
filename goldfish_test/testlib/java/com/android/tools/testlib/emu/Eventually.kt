package com.android.tools.testlib.emu

import java.lang.Thread

/**
 * Attempts op() until it returns true, or until count has been reached, with a delay of delay
 * milliseconds between each attempt.
 *
 * @return true if op() returned true, false otherwise.
 */
fun eventually(count: Int, delay: Long, op: () -> Boolean): Boolean {
  for (i in 1..count) {
    if (i > 1) {
      Thread.sleep(delay)
    }
    if (op()) {
      return true
    }
  }
  return false
}

/**
 * Attempts op() until it returns true. Defaults to 10 attempts with a 100ms delay between attempts.
 *
 * @return true if op() returned true, false otherwise.
 */
fun eventually(op: () -> Boolean): Boolean {
  return eventually(10, 100, op)
}
