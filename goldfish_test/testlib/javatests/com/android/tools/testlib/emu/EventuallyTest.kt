package com.android.tools.testlib.emu

import org.junit.Assert
import org.junit.Test

class EventuallyTest {

  @Test
  fun defaultsfirstSuccess() {
    Assert.assertTrue(
      eventually {
        true
      }
    )
  }

  @Test
  fun firstSuccess() {
    Assert.assertTrue(
      eventually(4, 1) {
        true
      }
    )
  }

  @Test
  fun laterSuccess() {
    var count = 0
    Assert.assertTrue(
      eventually(4, 1) {
        count++
        count == 2
      }
    )
  }

  @Test
  fun neverSuccess() {
    Assert.assertFalse(
      eventually(4, 1) {
        false
      }
    )
  }
}