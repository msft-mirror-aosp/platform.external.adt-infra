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


class MainActivity : Activity() {
    private var orientationListener: OrientationEventListener? = null
    val TAG = "aemu"
    private var mGLView: GLSurfaceView? = null

    override fun onCreate(savedInstanceState: Bundle?)  {
        super.onCreate(savedInstanceState)
        // Hide the status bar.
        window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_FULLSCREEN
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