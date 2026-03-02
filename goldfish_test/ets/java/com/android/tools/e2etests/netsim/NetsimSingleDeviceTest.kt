package com.android.tools.e2etests.netsim

import com.android.emulation.bluetooth.ChipKind
import com.android.tools.testlib.netsim.NetsimController
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import com.google.protobuf.Empty
import java.util.concurrent.TimeUnit
import netsim.frontend.Frontend.PatchDeviceRequest
import netsim.model.Model.Chip
import netsim.model.Model.Device
import netsim.model.Model.Orientation
import netsim.model.Model.Position
import org.junit.Assert
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(DeviceJUnit4ClassRunner::class)
class NetsimSingleDeviceTest : BaseHostJUnit4Test() {

  @Test
  fun deviceAttachesToNetsimd() {
    val resp =
      NetsimController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
        .listDevice(Empty.getDefaultInstance())

    Assert.assertTrue(resp.getDevicesCount() > 0)
  }

  @Test
  fun devicePatchAndReset() {
    val resp =
      NetsimController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
        .listDevice(Empty.getDefaultInstance())
    Assert.assertTrue(resp.getDevicesCount() > 0)

    // Patch the device's position and orientation.
    val patchPosition = Position.newBuilder().setX(1f).setY(2f).setZ(3f).build()
    val patchOrientation = Orientation.newBuilder().setYaw(30f).setPitch(60f).setRoll(90f).build()

    val name = resp.getDevices(0).getName()
    val req =
      PatchDeviceRequest.newBuilder()
        .setDevice(
          PatchDeviceRequest.PatchDeviceFields.newBuilder()
            .setName(name)
            .setPosition(patchPosition)
            .setOrientation(patchOrientation)
            .build()
        )
        .build()
    NetsimController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS).patchDevice(req)

    // Verify the patched position and orientation.
    val patchedResp =
      NetsimController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
        .listDevice(Empty.getDefaultInstance())
    val patchedDevice = getDevice(patchedResp.getDevicesList(), name)
    Assert.assertEquals(patchedDevice.getPosition(), patchPosition)
    Assert.assertEquals(patchedDevice.getOrientation(), patchOrientation)

    // Reset and verify position and orientation.
    NetsimController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
      .reset(Empty.getDefaultInstance())
    val resetResp =
      NetsimController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
        .listDevice(Empty.getDefaultInstance())
    val resetDevice = getDevice(resetResp.getDevicesList(), name)
    Assert.assertEquals(resetDevice.getPosition(), Position.getDefaultInstance())
    Assert.assertEquals(resetDevice.getOrientation(), Orientation.getDefaultInstance())
  }

  @Test
  fun netsimRadioStateToggle() {
    val resp =
      NetsimController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
        .listDevice(Empty.getDefaultInstance())
    Assert.assertTrue(resp.getDevicesCount() > 0)

    // Turn off Radio State (BLE) and verify.
    val name = resp.getDevices(0).getName()
    NetsimController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
      .patchDevice(patchBleStateRequest(name, false))

    var patchedResp =
      NetsimController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
        .listDevice(Empty.getDefaultInstance())
    assertBleState(getDevice(patchedResp.getDevicesList(), name), false)

    // Turn on Radio State (BLE) and verify.
    NetsimController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
      .patchDevice(patchBleStateRequest(name, true))

    patchedResp =
      NetsimController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
        .listDevice(Empty.getDefaultInstance())
    assertBleState(getDevice(patchedResp.getDevicesList(), name), true)

    // Turn off Radio State (BLE), reset and verify.
    NetsimController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
      .patchDevice(patchBleStateRequest(name, false))
    NetsimController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
      .reset(Empty.getDefaultInstance())

    patchedResp =
      NetsimController.stub!!.withDeadlineAfter(10, TimeUnit.SECONDS)
        .listDevice(Empty.getDefaultInstance())
    assertBleState(getDevice(patchedResp.getDevicesList(), name), true)
  }
}

fun getDevice(devices: List<Device>, name: String): Device {
  for (device in devices) {
    if (device.getName() == name) {
      return device
    }
  }
  Assert.fail("No device named: " + name)
  return Device.getDefaultInstance()
}

fun patchBleStateRequest(name: String, state: Boolean): PatchDeviceRequest {
  return PatchDeviceRequest.newBuilder()
    .setDevice(
      PatchDeviceRequest.PatchDeviceFields.newBuilder()
        .setName(name)
        .addChips(
          Chip.newBuilder()
            .setBt(
              Chip.Bluetooth.newBuilder()
                .setLowEnergy(Chip.Radio.newBuilder().setState(state).build())
                .build()
            )
            .build()
        )
        .build()
    )
    .build()
}

fun assertBleState(device: Device, state: Boolean) {
  for (chip in device.getChipsList()) {
    if (chip.getKind() == ChipKind.BLUETOOTH) {
      Assert.assertEquals(chip.getBt().getLowEnergy().getState(), state)
    }
  }
}
