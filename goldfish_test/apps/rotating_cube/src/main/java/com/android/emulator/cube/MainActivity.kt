package com.android.emulator.cube

import android.app.Activity
import android.graphics.Color
import android.opengl.GLSurfaceView
import android.os.Bundle
import android.widget.FrameLayout
import android.widget.TextView

class MainActivity : Activity() {
    private lateinit var glView: GLSurfaceView
    private lateinit var fpsTextView: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val layout = FrameLayout(this)
        
        fpsTextView = TextView(this).apply {
            setTextColor(Color.GREEN)
            textSize = 24f
            text = "FPS: --"
            setPadding(32, 32, 32, 32)
        }

        glView = GLSurfaceView(this).apply {
            setEGLContextClientVersion(2)
            setEGLWindowSurfaceFactory(object : GLSurfaceView.EGLWindowSurfaceFactory {
                override fun createWindowSurface(
                    egl: javax.microedition.khronos.egl.EGL10,
                    display: javax.microedition.khronos.egl.EGLDisplay,
                    config: javax.microedition.khronos.egl.EGLConfig,
                    nativeWindow: Any
                ): javax.microedition.khronos.egl.EGLSurface? {
                    val result = egl.eglCreateWindowSurface(display, config, nativeWindow, null)
                    android.opengl.EGL14.eglSwapInterval(
                        android.opengl.EGL14.eglGetDisplay(android.opengl.EGL14.EGL_DEFAULT_DISPLAY),
                        0
                    )
                    return result
                }

                override fun destroySurface(
                    egl: javax.microedition.khronos.egl.EGL10,
                    display: javax.microedition.khronos.egl.EGLDisplay,
                    surface: javax.microedition.khronos.egl.EGLSurface
                ) {
                    egl.eglDestroySurface(display, surface)
                }
            })
            setRenderer(CubeRenderer { fps ->
                runOnUiThread {
                    fpsTextView.text = String.format("FPS: %.1f", fps)
                }
            })
            renderMode = GLSurfaceView.RENDERMODE_CONTINUOUSLY
        }
        
        layout.addView(glView)
        layout.addView(fpsTextView)
        
        setContentView(layout)
    }

    override fun onResume() {
        super.onResume()
        glView.onResume()
    }

    override fun onPause() {
        super.onPause()
        glView.onPause()
    }
}
