package com.android.emulator.cube

import android.opengl.GLES20
import android.opengl.GLSurfaceView
import android.opengl.Matrix
import android.os.SystemClock
import android.util.Log
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import java.nio.ShortBuffer
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10

class CubeRenderer(private val onFpsUpdate: ((Float) -> Unit)? = null) : GLSurfaceView.Renderer {
    companion object {
        private const val TAG = "RotatingCube"
        private const val VERTEX_SHADER_CODE = """
            uniform mat4 uMVPMatrix;
            attribute vec4 aPosition;
            attribute vec4 aColor;
            varying vec4 vColor;
            void main() {
                gl_Position = uMVPMatrix * aPosition;
                vColor = aColor;
            }
        """

        private const val FRAGMENT_SHADER_CODE = """
            precision mediump float;
            varying vec4 vColor;
            void main() {
                gl_FragColor = vColor;
            }
        """
    }

    private val vertexCoords = floatArrayOf(
        // Front face (Red)
        -0.5f, -0.5f,  0.5f,  1f, 0f, 0f, 1f,
         0.5f, -0.5f,  0.5f,  1f, 0f, 0f, 1f,
         0.5f,  0.5f,  0.5f,  1f, 0f, 0f, 1f,
        -0.5f,  0.5f,  0.5f,  1f, 0f, 0f, 1f,

        // Back face (Green)
        -0.5f, -0.5f, -0.5f,  0f, 1f, 0f, 1f,
        -0.5f,  0.5f, -0.5f,  0f, 1f, 0f, 1f,
         0.5f,  0.5f, -0.5f,  0f, 1f, 0f, 1f,
         0.5f, -0.5f, -0.5f,  0f, 1f, 0f, 1f,

        // Top face (Blue)
        -0.5f,  0.5f, -0.5f,  0f, 0f, 1f, 1f,
        -0.5f,  0.5f,  0.5f,  0f, 0f, 1f, 1f,
         0.5f,  0.5f,  0.5f,  0f, 0f, 1f, 1f,
         0.5f,  0.5f, -0.5f,  0f, 0f, 1f, 1f,

        // Bottom face (Yellow)
        -0.5f, -0.5f, -0.5f,  1f, 1f, 0f, 1f,
         0.5f, -0.5f, -0.5f,  1f, 1f, 0f, 1f,
         0.5f, -0.5f,  0.5f,  1f, 1f, 0f, 1f,
        -0.5f, -0.5f,  0.5f,  1f, 1f, 0f, 1f,

        // Right face (Cyan)
         0.5f, -0.5f, -0.5f,  0f, 1f, 1f, 1f,
         0.5f,  0.5f, -0.5f,  0f, 1f, 1f, 1f,
         0.5f,  0.5f,  0.5f,  0f, 1f, 1f, 1f,
         0.5f, -0.5f,  0.5f,  0f, 1f, 1f, 1f,

        // Left face (Magenta)
        -0.5f, -0.5f, -0.5f,  1f, 0f, 1f, 1f,
        -0.5f, -0.5f,  0.5f,  1f, 0f, 1f, 1f,
        -0.5f,  0.5f,  0.5f,  1f, 0f, 1f, 1f,
        -0.5f,  0.5f, -0.5f,  1f, 0f, 1f, 1f
    )

    private val drawOrder = shortArrayOf(
         0,  1,  2,   0,  2,  3, // Front
         4,  5,  6,   4,  6,  7, // Back
         8,  9, 10,   8, 10, 11, // Top
        12, 13, 14,  12, 14, 15, // Bottom
        16, 17, 18,  16, 18, 19, // Right
        20, 21, 22,  20, 22, 23  // Left
    )

    private lateinit var vertexBuffer: FloatBuffer
    private lateinit var drawListBuffer: ShortBuffer
    private var program = 0

    private val mvpMatrix = FloatArray(16)
    private val projectionMatrix = FloatArray(16)
    private val viewMatrix = FloatArray(16)
    private val rotationMatrix = FloatArray(16)
    private val modelMatrix = FloatArray(16)

    private var frameCount = 0L
    private var lastFpsLogTime = 0L
    private var framesInSecond = 0

    override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
        GLES20.glClearColor(0.1f, 0.1f, 0.12f, 1.0f)
        GLES20.glEnable(GLES20.GL_DEPTH_TEST)

        val bb = ByteBuffer.allocateDirect(vertexCoords.size * 4)
        bb.order(ByteOrder.nativeOrder())
        vertexBuffer = bb.asFloatBuffer()
        vertexBuffer.put(vertexCoords)
        vertexBuffer.position(0)

        val dlb = ByteBuffer.allocateDirect(drawOrder.size * 2)
        dlb.order(ByteOrder.nativeOrder())
        drawListBuffer = dlb.asShortBuffer()
        drawListBuffer.put(drawOrder)
        drawListBuffer.position(0)

        val vertexShader = loadShader(GLES20.GL_VERTEX_SHADER, VERTEX_SHADER_CODE)
        val fragmentShader = loadShader(GLES20.GL_FRAGMENT_SHADER, FRAGMENT_SHADER_CODE)

        program = GLES20.glCreateProgram().also {
            GLES20.glAttachShader(it, vertexShader)
            GLES20.glAttachShader(it, fragmentShader)
            GLES20.glLinkProgram(it)
        }

        Matrix.setLookAtM(viewMatrix, 0, 0f, 0f, -3.5f, 0f, 0f, 0f, 0f, 1.0f, 0.0f)
        lastFpsLogTime = SystemClock.elapsedRealtime()
        Log.i(TAG, "--STARTED-- (RotatingCube initialized)")
    }

    override fun onSurfaceChanged(gl: GL10?, width: Int, height: Int) {
        GLES20.glViewport(0, 0, width, height)
        val ratio = width.toFloat() / height.toFloat()
        Matrix.frustumM(projectionMatrix, 0, -ratio, ratio, -1f, 1f, 2f, 10f)
    }

    override fun onDrawFrame(gl: GL10?) {
        frameCount++
        framesInSecond++
        val now = SystemClock.elapsedRealtime()
        if (now - lastFpsLogTime >= 1000) {
            val fps = (framesInSecond * 1000.0f) / (now - lastFpsLogTime)
            Log.d(TAG, "Rendering at $fps FPS (total frames: $frameCount)")
            onFpsUpdate?.invoke(fps)
            framesInSecond = 0
            lastFpsLogTime = now
        }

        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT or GLES20.GL_DEPTH_BUFFER_BIT)
        GLES20.glUseProgram(program)

        val positionHandle = GLES20.glGetAttribLocation(program, "aPosition")
        val colorHandle = GLES20.glGetAttribLocation(program, "aColor")
        val mvpMatrixHandle = GLES20.glGetUniformLocation(program, "uMVPMatrix")

        val stride = 7 * 4 // 3 coords + 4 colors = 7 floats * 4 bytes
        vertexBuffer.position(0)
        GLES20.glEnableVertexAttribArray(positionHandle)
        GLES20.glVertexAttribPointer(positionHandle, 3, GLES20.GL_FLOAT, false, stride, vertexBuffer)

        vertexBuffer.position(3)
        GLES20.glEnableVertexAttribArray(colorHandle)
        GLES20.glVertexAttribPointer(colorHandle, 4, GLES20.GL_FLOAT, false, stride, vertexBuffer)

        // Rotate smoothly over time
        val angle = (SystemClock.uptimeMillis() % 4000L) * (360f / 4000f)
        Matrix.setRotateM(rotationMatrix, 0, angle, 0.6f, 1.0f, 0.4f)
        Matrix.multiplyMM(modelMatrix, 0, viewMatrix, 0, rotationMatrix, 0)
        Matrix.multiplyMM(mvpMatrix, 0, projectionMatrix, 0, modelMatrix, 0)

        GLES20.glUniformMatrix4fv(mvpMatrixHandle, 1, false, mvpMatrix, 0)
        GLES20.glDrawElements(GLES20.GL_TRIANGLES, drawOrder.size, GLES20.GL_UNSIGNED_SHORT, drawListBuffer)

        GLES20.glDisableVertexAttribArray(positionHandle)
        GLES20.glDisableVertexAttribArray(colorHandle)
    }

    private fun loadShader(type: Int, shaderCode: String): Int {
        return GLES20.glCreateShader(type).also { shader ->
            GLES20.glShaderSource(shader, shaderCode)
            GLES20.glCompileShader(shader)
        }
    }
}
