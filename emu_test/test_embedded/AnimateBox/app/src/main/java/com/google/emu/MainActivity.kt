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

class MainActivity : Activity() {
    val TAG = "aemu"
    private var mGLView: GLSurfaceView? = null


    override fun onCreate(savedInstanceState: Bundle?)  {
        super.onCreate(savedInstanceState)
        // Create a GLSurfaceView instance and set it
        // as the ContentView for this Activity
        mGLView = MyGLSurfaceView(this)
        setContentView(mGLView)
    }

    override  protected fun onPause() {
        super.onPause()
        mGLView!!.onPause()
    }

    override  protected fun onResume() {
        super.onResume()
        mGLView!!.onResume()
    }


}