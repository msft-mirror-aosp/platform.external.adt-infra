package com.android.tools.e2etests.clipboard

import android.app.Activity
import android.content.ClipboardManager
import android.content.Context
import android.os.Bundle
import android.view.View
import androidx.test.ext.junit.rules.ActivityScenarioRule
import androidx.test.platform.app.InstrumentationRegistry
import com.android.emulator.control.ClipData
import com.android.tools.e2etests.grpc.EmulatorController
import com.android.tools.testlib.emu.eventually
import com.google.protobuf.Empty
import com.google.testing.junit.testparameterinjector.TestParameter
import com.google.testing.junit.testparameterinjector.TestParameterInjector
import org.junit.Assert
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

val TAG = "ClipboardTest"

class MainActivity : Activity() {
  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    setContentView(View(this))
  }
}

@RunWith(TestParameterInjector::class)
class ClipboardTest {

  // Launches the activity before the test starts, putting it in the foreground.
  // This is required for the clipboard to be accessed.
  @get:Rule val activityRule = ActivityScenarioRule(MainActivity::class.java)

  enum class TestCase(val text: String) {
    HELLO_THERE("Hello There!"),
    HOW_IS_THE_WEATHER("How Is The Weather?"),
  }

  @Test
  fun setInAndroidGetInGrpc(@TestParameter testCase: TestCase) {
    setClipboardText(testCase.text)
    Assert.assertTrue(
      eventually(30, 100) {
        EmulatorController.defaultDeadline().getClipboard(Empty.getDefaultInstance()).getText() ==
          testCase.text
      }
    )
  }

  @Test
  fun setInGrpcGetInAndroid(@TestParameter testCase: TestCase) {
    EmulatorController.defaultDeadline()
      .setClipboard(ClipData.newBuilder().setText(testCase.text).build())
    Assert.assertTrue(eventually(30, 100) { getClipboardText() == testCase.text })
  }
}

fun getClipboardText(): String {
  val instrumentation = InstrumentationRegistry.getInstrumentation()
  var clipboardText = ""

  // ClipboardManager must be accessed on the main thread in tests
  instrumentation.runOnMainSync {
    val clipboardManager =
      instrumentation.targetContext.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager

    val clipData = clipboardManager.primaryClip
    if (clipData != null && clipData.itemCount > 0) {
      clipboardText = clipData.getItemAt(0).text?.toString() ?: ""
    }
  }

  return clipboardText
}

fun setClipboardText(text: String) {
  val instrumentation = InstrumentationRegistry.getInstrumentation()

  // ClipboardManager must be accessed on the main thread in tests
  instrumentation.runOnMainSync {
    val clipboardManager =
      instrumentation.targetContext.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
    clipboardManager.setPrimaryClip(android.content.ClipData.newPlainText("label", text))
  }
}
