package com.android.tools.e2etests.input

object TestConstants {
  const val DEFAULT_TIMEOUT_MS = 5000L
  const val DEFAULT_TIMEOUT_SECONDS = 5L
}

/** Constants for Linux evdev event types and codes. Used to avoid magic numbers in input tests. */
object EvDev {
  // Event Types
  const val EV_SYN = 0
  const val EV_KEY = 1
  const val EV_REL = 2
  const val EV_ABS = 3

  // Synchronization Codes
  const val SYN_REPORT = 0

  // Key Codes
  const val KEY_A = 30
  const val KEY_B = 48
  const val KEY_H = 35
  const val KEY_HOME = 102
  const val KEY_LEFTSHIFT = 42
  const val KEY_BACK = 158
  const val KEY_APP_SWITCH = 580
  const val BTN_TOOL_RUBBER = 321
  const val BTN_STYLUS = 330

  // Absolute Axis Codes
  const val ABS_X = 0
  const val ABS_Y = 1
  const val ABS_Z = 2
  const val ABS_MT_SLOT = 47
  const val ABS_MT_TOUCH_MAJOR = 48
  const val ABS_MT_TOUCH_MINOR = 49
  const val ABS_MT_ORIENTATION = 52
  const val ABS_MT_POSITION_X = 53
  const val ABS_MT_POSITION_Y = 54
  const val ABS_MT_TOOL_TYPE = 55
  const val ABS_MT_TRACKING_ID = 57
  const val ABS_MT_PRESSURE = 58
}
