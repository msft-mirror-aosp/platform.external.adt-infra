package com.android.tools.testlib.emu

import android.app.UiAutomation
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
   * @param filter adb filter expression (<module>:<level>) All other lines are discarded.
   * @return the output of the command.
   */
  fun logcat(filter: String): List<String> {
    return shell("logcat -d $filter *:S")
  }
}

/**
 * Handles watching ADB logcat for new lines.
 *
 * To avoid clearing the logcat and potentially interfering with other tests, this class watches for
 * new lines in the logcat output and only returns true if the desired string is found after the
 * last line in the initial logcat output.
 *
 * @property adb the ADB instance to use for ADB operations.
 * @property filter adb filter expression (<module>:<level>)
 */
class LogcatWatcher(val adb: Adb, val filter: String) {
  private var lastLine: String

  init {
    val lines = adb.logcat(filter)
    if (lines.isEmpty()) {
      lastLine = ""
    } else {
      lastLine = lines.last()
    }
  }

  /**
   * Returns true if the desired string is found in the logcat output after the last line in the
   * initial logcat output.
   *
   * The last line is updated to the latest line in the logcat output.
   *
   * @param want the string to search for.
   * @return true if the desired string is found.
   */
  fun containsNewLine(want: String): Boolean {
    var found = false
    if (lastLine == "") {
      found = true
    }
    for (line in adb.logcat(filter)) {
      if (!found && line == lastLine) {
        found = true
        continue
      }
      if (found && line.contains(want)) {
        lastLine = line
        return true
      }
    }
    return false
  }
}
