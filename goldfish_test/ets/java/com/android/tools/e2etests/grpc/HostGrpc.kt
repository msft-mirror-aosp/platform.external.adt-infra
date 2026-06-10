package com.android.tools.e2etests.grpc

import com.android.tools.testlib.emu.Discovery
import com.android.tools.testlib.emu.findEmulator
import io.grpc.Grpc
import io.grpc.InsecureChannelCredentials

fun getHostGrpcChannel(serialNumber: String): io.grpc.ManagedChannel {
  return getHostGrpcChannel(findEmulator(serialNumber)!!)
}

fun getHostGrpcChannel(discovery: Discovery): io.grpc.ManagedChannel {
  val port = discovery!!.discoveryIni["grpc.port"]
  return Grpc.newChannelBuilder("localhost:" + port, InsecureChannelCredentials.create()).build()
}