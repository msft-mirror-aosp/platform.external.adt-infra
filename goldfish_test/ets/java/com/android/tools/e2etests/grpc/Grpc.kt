package com.android.tools.e2etests.grpc

import android.util.Log
import androidx.test.platform.app.InstrumentationRegistry
import com.android.emulator.control.EmulatorControllerGrpc
import com.android.emulator.control.UiControllerGrpc
import com.android.emulator.control.RtcGrpc
import com.android.emulation.control.incubating.AvdServiceGrpc
import com.android.emulation.control.incubating.CarServiceGrpc
import com.android.emulation.control.incubating.ModemGrpc
import com.android.emulation.control.incubating.ScreenRecordingGrpc
import com.android.emulation.control.incubating.SensorServiceGrpc
import com.android.emulation.control.incubating.VirtualSceneServiceGrpc
import com.google.waterfall.WaterfallGrpc
import io.grpc.InsecureChannelCredentials
import io.grpc.okhttp.OkHttpChannelBuilder
import java.util.concurrent.TimeUnit

const val TAG = "EmuGrpc"

/**
 * Shared channel for all grpc stubs to avoid creating multiple connections.
 */
object GrpcChannel {
  val instance: io.grpc.ManagedChannel by lazy {
    val grpcPort = InstrumentationRegistry.getArguments().getString("grpc-port", "0")
    Log.i(TAG, "Using grpc port: " + grpcPort)
    OkHttpChannelBuilder.forAddress(
      "10.0.2.2",
      grpcPort.toInt(),
      InsecureChannelCredentials.create(),
    )
    .build()
  }
}

object EmulatorController {
  var asyncStub: EmulatorControllerGrpc.EmulatorControllerStub? = null
  var stub: EmulatorControllerGrpc.EmulatorControllerBlockingStub? = null

  init {
    stub = EmulatorControllerGrpc.newBlockingStub(GrpcChannel.instance)
    asyncStub = EmulatorControllerGrpc.newStub(GrpcChannel.instance)
  }

  fun asyncDefaultDeadline(): EmulatorControllerGrpc.EmulatorControllerStub {
    return asyncStub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
  }

  fun defaultDeadline(): EmulatorControllerGrpc.EmulatorControllerBlockingStub {
    return stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
  }
}

object AvdService {
  var asyncStub: AvdServiceGrpc.AvdServiceStub? = null
  var stub: AvdServiceGrpc.AvdServiceBlockingStub? = null

  init {
    stub = AvdServiceGrpc.newBlockingStub(GrpcChannel.instance)
    asyncStub = AvdServiceGrpc.newStub(GrpcChannel.instance)
  }
}

object CarService {
  var asyncStub: CarServiceGrpc.CarServiceStub? = null
  var stub: CarServiceGrpc.CarServiceBlockingStub? = null

  init {
    stub = CarServiceGrpc.newBlockingStub(GrpcChannel.instance)
    asyncStub = CarServiceGrpc.newStub(GrpcChannel.instance)
  }
}

object ModemService {
  var asyncStub: ModemGrpc.ModemStub? = null
  var stub: ModemGrpc.ModemBlockingStub? = null

  init {
    stub = ModemGrpc.newBlockingStub(GrpcChannel.instance)
    asyncStub = ModemGrpc.newStub(GrpcChannel.instance)
  }
}

object ScreenRecordingService {
  var asyncStub: ScreenRecordingGrpc.ScreenRecordingStub? = null
  var stub: ScreenRecordingGrpc.ScreenRecordingBlockingStub? = null

  init {
    stub = ScreenRecordingGrpc.newBlockingStub(GrpcChannel.instance)
    asyncStub = ScreenRecordingGrpc.newStub(GrpcChannel.instance)
  }
}

object SensorService {
  var asyncStub: SensorServiceGrpc.SensorServiceStub? = null
  var stub: SensorServiceGrpc.SensorServiceBlockingStub? = null

  init {
    stub = SensorServiceGrpc.newBlockingStub(GrpcChannel.instance)
    asyncStub = SensorServiceGrpc.newStub(GrpcChannel.instance)
  }
}

object VirtualSceneService {
  var asyncStub: VirtualSceneServiceGrpc.VirtualSceneServiceStub? = null
  var stub: VirtualSceneServiceGrpc.VirtualSceneServiceBlockingStub? = null

  init {
    stub = VirtualSceneServiceGrpc.newBlockingStub(GrpcChannel.instance)
    asyncStub = VirtualSceneServiceGrpc.newStub(GrpcChannel.instance)
  }
}

object UiControllerService {
  var asyncStub: UiControllerGrpc.UiControllerStub? = null
  var stub: UiControllerGrpc.UiControllerBlockingStub? = null

  init {
    stub = UiControllerGrpc.newBlockingStub(GrpcChannel.instance)
    asyncStub = UiControllerGrpc.newStub(GrpcChannel.instance)
  }
}

object WaterfallService {
  var asyncStub: WaterfallGrpc.WaterfallStub? = null
  var stub: WaterfallGrpc.WaterfallBlockingStub? = null

  init {
    stub = WaterfallGrpc.newBlockingStub(GrpcChannel.instance)
    asyncStub = WaterfallGrpc.newStub(GrpcChannel.instance)
  }
}

object RtcService {
  var asyncStub: RtcGrpc.RtcStub? = null
  var stub: RtcGrpc.RtcBlockingStub? = null

  init {
    stub = RtcGrpc.newBlockingStub(GrpcChannel.instance)
    asyncStub = RtcGrpc.newStub(GrpcChannel.instance)
  }
}
