package com.android.tools.testlib.emu

import android.app.UiAutomation
import android.os.ParcelFileDescriptor
import java.io.FileInputStream

/**
 * Handles common ADB operations for emulator tests.
 *
 * @property uiAutomation the UiAutomation to use for ADB operations.
 */
class Adb(val uiAutomation: UiAutomation) {

  /**
   * Executes an ADB shell command and returns the output.
   *
   * @param command the command to execute.
   * @return the output of the command.
   */
  fun shell(command: String): List<String> {
    val fd = uiAutomation.executeShellCommand(command)
    return FileInputStream(fd.getFileDescriptor()).bufferedReader(charset = Charsets.UTF_8).use {
      reader ->
      reader.readLines()
    }
  }

  /**
   * Returns the logcat output from the emulator.
   *
   * @param filter regular expression to filter the logcat output.
   * @return the output of the command.
   */
  fun logcat(filter: String): List<String> {
    val lines = shell("logcat -d")
    val regex = filter.toRegex()
    return lines.filter { regex.containsMatchIn(it) }
  }
}
