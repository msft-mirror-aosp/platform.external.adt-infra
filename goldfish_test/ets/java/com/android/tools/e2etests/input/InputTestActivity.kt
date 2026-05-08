package com.android.tools.e2etests.input

import android.app.Activity
import android.os.Bundle
import android.util.Log
import android.view.KeyEvent
import android.view.MotionEvent
import java.util.concurrent.CopyOnWriteArrayList
import androidx.test.platform.app.InstrumentationRegistry

class InputTestActivity : Activity() {

  companion object {
    val touchEvents = CopyOnWriteArrayList<TouchEventInfo>()
    val keyEvents = CopyOnWriteArrayList<KeyEventInfo>()
    val genericMotionEvents = CopyOnWriteArrayList<GenericMotionEventInfo>()
    var currentEditText: android.widget.EditText? = null
      private set

    var focusLatch = java.util.concurrent.CountDownLatch(1)

    fun clearEvents() {
      touchEvents.clear()
      keyEvents.clear()
      genericMotionEvents.clear()
      InstrumentationRegistry.getInstrumentation().runOnMainSync {
        currentEditText?.text?.clear()
      }
    }

    fun finishActivity() {
      currentEditText?.post {
        (currentEditText?.context as? android.app.Activity)?.finish()
      }
    }
  }

  data class TouchEventInfo(
      val action: Int,
      val x: Float,
      val y: Float,
      val timeNanos: Long,
      val pointerCount: Int,
      val pressure: Float,
      val toolType: Int,
  )

  data class KeyEventInfo(val action: Int, val keyCode: Int, val timeNanos: Long)

  data class GenericMotionEventInfo(
      val action: Int,
      val x: Float,
      val y: Float,
      val timeNanos: Long,
      val axisScroll: Float,
  )

  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    val layout =
        android.widget.LinearLayout(this).apply {
          orientation = android.widget.LinearLayout.VERTICAL
        }

    val editText =
        object : android.widget.EditText(this) {
              override fun onCreateInputConnection(
                  outAttrs: android.view.inputmethod.EditorInfo?
              ): android.view.inputmethod.InputConnection? {
                return null
              }
            }
            .apply {
              id = android.view.View.generateViewId()
              showSoftInputOnFocus = false
            }
    layout.addView(editText)

    val touchView =
        android.view.View(this).apply {
          layoutParams =
              android.widget.LinearLayout.LayoutParams(
                  android.widget.LinearLayout.LayoutParams.MATCH_PARENT,
                  android.widget.LinearLayout.LayoutParams.MATCH_PARENT,
              )
          setOnTouchListener { _, event ->
            Log.d(
                "InputTestActivity",
                "onTouch: action=${event.action}, x=${event.rawX}, y=${event.rawY}",
            )
            touchEvents.add(
                TouchEventInfo(
                    event.action,
                    event.rawX,
                    event.rawY,
                    System.nanoTime(),
                    event.pointerCount,
                    event.pressure,
                    event.getToolType(0),
                )
            )
            true
          }
          setOnGenericMotionListener { _, event ->
            Log.d(
                "InputTestActivity",
                "onGenericMotion: action=${event.action}, x=${event.rawX}, y=${event.rawY}",
            )
            genericMotionEvents.add(
                GenericMotionEventInfo(
                    event.action,
                    event.rawX,
                    event.rawY,
                    System.nanoTime(),
                    event.getAxisValue(MotionEvent.AXIS_VSCROLL),
                )
            )
            true
          }
        }
    layout.addView(touchView)

    setContentView(layout)

    editText.requestFocus()
    currentEditText = editText
  }

  override fun dispatchKeyEvent(event: android.view.KeyEvent): Boolean {
    Log.d("InputTestActivity", "dispatchKeyEvent: action=${event.action}, keyCode=${event.keyCode}")
    keyEvents.add(KeyEventInfo(event.action, event.keyCode, System.nanoTime()))
    return super.dispatchKeyEvent(event)
  }

  override fun onDestroy() {
    super.onDestroy()
    currentEditText = null
  }

  override fun onWindowFocusChanged(hasFocus: Boolean) {
    super.onWindowFocusChanged(hasFocus)
    Log.d("InputTestActivity", "onWindowFocusChanged: hasFocus=$hasFocus")
    if (hasFocus) {
      focusLatch.countDown()
    }
  }
}
