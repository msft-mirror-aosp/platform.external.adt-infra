package com.android.tools.e2etests.grpc

import android.util.Log
import androidx.test.platform.app.InstrumentationRegistry
import com.android.emulator.control.EmulatorControllerGrpc
import io.grpc.InsecureChannelCredentials
import io.grpc.okhttp.OkHttpChannelBuilder
import java.util.concurrent.TimeUnit

const val TAG = "EmuGrpc"

/**
 * Singleton for sharing a grpc stub across tests.
 *
 * @property stub the grpc stub.
 */
object EmulatorController {
  var stub: EmulatorControllerGrpc.EmulatorControllerBlockingStub? = null

  init {
    val grpcPort = InstrumentationRegistry.getArguments().getString("grpc-port", "0")
    Log.i(TAG, "Using grpc port: " + grpcPort)
    val channel =
      OkHttpChannelBuilder.forAddress(
          "10.0.2.2",
          grpcPort.toInt(),
          InsecureChannelCredentials.create(),
        )
        .build()
    stub = EmulatorControllerGrpc.newBlockingStub(channel)
  }

  fun defaultDeadline(): EmulatorControllerGrpc.EmulatorControllerBlockingStub {
    return stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
  }
}
