package com.google.emu

import android.app.Activity
import android.content.ClipboardManager
import android.opengl.GLSurfaceView
import android.os.Bundle
import android.os.SystemClock
import android.util.Log
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.OrientationEventListener
import com.android.emulator.control.MouseEvent
import com.google.protobuf.MessageOrBuilder
import com.google.protobuf.util.JsonFormat
import android.hardware.SensorManager
import android.view.View
import com.android.emulator.control.KeyboardEvent


class MainActivity : Activity() {
    private var orientationListener: OrientationEventListener? = null
    val TAG = "aemu"
    private var mGLView: MyGLSurfaceView? = null

    override fun onCreate(savedInstanceState: Bundle?)  {
        super.onCreate(savedInstanceState)
        // Hide the status bar.
        window.decorView.systemUiVisibility =
            View.SYSTEM_UI_FLAG_FULLSCREEN or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
        actionBar?.hide()
        // Create a GLSurfaceView instance and set it
        // as the ContentView for this Activity
        mGLView = MyGLSurfaceView(this)
        setContentView(mGLView)
        orientationListener =
            object : OrientationEventListener(this, SensorManager.SENSOR_DELAY_UI) {
                override fun onOrientationChanged(orientation: Int) {
                    Log.i(TAG, "Rotation: $orientation")
                }
            }

    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        val key = KeyboardEvent.newBuilder().setKey(JsonLogger.translateKeyEvent(event))
            .setEventType(KeyboardEvent.KeyEventType.keydown).build()
        Log.i(TAG, JsonLogger.toJson("KeyboardEvent", key))

        if (keyCode == KeyEvent.KEYCODE_P) {
            mGLView!!.mPaused = true
        } else if (keyCode == KeyEvent.KEYCODE_R) {
            mGLView!!.mPaused = false
        }
        return true
    }


    override fun onKeyUp(keyCode: Int, event: KeyEvent): Boolean {
        val key = KeyboardEvent.newBuilder().setKey(JsonLogger.translateKeyEvent(event))
            .setEventType(KeyboardEvent.KeyEventType.keyup).build()
        Log.i(TAG, JsonLogger.toJson("KeyboardEvent", key))

        return true
    }


    override  protected fun onPause() {
        super.onPause()
        mGLView!!.onPause()
        orientationListener!!.disable()
    }

    override  protected fun onResume() {
        super.onResume()
        mGLView!!.onResume()
        orientationListener!!.enable()
    }


}
