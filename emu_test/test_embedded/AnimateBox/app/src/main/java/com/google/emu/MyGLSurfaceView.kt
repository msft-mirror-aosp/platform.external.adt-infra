package com.google.emu

import android.content.Context
import android.opengl.GLSurfaceView
import android.util.Log
import android.view.KeyEvent
import android.view.MotionEvent
import com.android.emulator.control.KeyboardEvent
import com.android.emulator.control.MouseEvent


class MyGLSurfaceView(context: Context?) : GLSurfaceView(context) {

    private val TAG = "aemu"
    private val mRenderer: MyGLRenderer
    private val TOUCH_SCALE_FACTOR = 180.0f / 320
    private var mPreviousX = 0f
    private var mPreviousY = 0f

    var mPaused = false

    override fun onTouchEvent(event: MotionEvent): Boolean {
        // MotionEvent reports input details from the touch screen
        // and other input controls. In this case, you are only
        // interested in events where the touch position changed.
        val btns = when (event.actionMasked) {
            MotionEvent.ACTION_DOWN, MotionEvent.ACTION_POINTER_DOWN -> 1
            else -> 0
        }

        val mouse =
            MouseEvent.newBuilder().setX(event.rawX.toInt()).setY(event.rawY.toInt())
                .setButtons(btns)
                .build()

        Log.i(TAG, JsonLogger.toJson("MouseEvent", mouse))
        return true
    }




    init {
        // Create an OpenGL ES 2.0 context.
        setEGLContextClientVersion(2)
        // Set the Renderer for drawing on the GLSurfaceView
        mRenderer = MyGLRenderer()
        setRenderer(mRenderer)
        // Render the view only when there is a change in the drawing data
        renderMode = RENDERMODE_WHEN_DIRTY

        val thread = Thread {
            var frame = 0
            var paused = mPaused
            while (true) {
                if (paused != mPaused) {
                    paused = mPaused
                    if (paused)
                        Log.i(TAG, "Pausing animation.")
                    else
                        Log.i(TAG, "Resuming animation.")
                }
                if (!paused) {
                    mRenderer.angle += 1
                    mRenderer.color = frame++;
                }
                requestRender()
                Thread.sleep(10);
            }
        }
        thread.start()

    }
}