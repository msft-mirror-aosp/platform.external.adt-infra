package com.android.tools.e2etests.netsim

import com.android.emulation.bluetooth.ChipKind
import com.android.tools.testlib.netsim.NetsimController
import com.android.tradefed.testtype.DeviceJUnit4ClassRunner
import com.android.tradefed.testtype.junit4.BaseHostJUnit4Test
import com.google.protobuf.Empty
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
    val resp = NetsimController.defaultDeadline().listDevice(Empty.getDefaultInstance())

    Assert.assertTrue(resp.getDevicesCount() > 0)
  }

  @Test
  fun devicePatchAndReset() {
    val resp = NetsimController.defaultDeadline().listDevice(Empty.getDefaultInstance())
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
    NetsimController.defaultDeadline().patchDevice(req)

    // Verify the patched position and orientation.
    val patchedResp = NetsimController.defaultDeadline().listDevice(Empty.getDefaultInstance())
    val patchedDevice = getDevice(patchedResp.getDevicesList(), name)
    Assert.assertEquals(patchedDevice.getPosition(), patchPosition)
    Assert.assertEquals(patchedDevice.getOrientation(), patchOrientation)

    // Reset and verify position and orientation.
    NetsimController.defaultDeadline().reset(Empty.getDefaultInstance())
    val resetResp = NetsimController.defaultDeadline().listDevice(Empty.getDefaultInstance())
    val resetDevice = getDevice(resetResp.getDevicesList(), name)
    Assert.assertEquals(resetDevice.getPosition(), Position.getDefaultInstance())
    Assert.assertEquals(resetDevice.getOrientation(), Orientation.getDefaultInstance())
  }

  @Test
  fun netsimRadioStateToggle() {
    // Select the attached emulator Bluetooth device rather than built-in BLE beacons.
    val name = waitForBluetoothDeviceName()
    NetsimController.defaultDeadline().patchDevice(patchBleStateRequest(name, false))

    var patchedResp = NetsimController.defaultDeadline().listDevice(Empty.getDefaultInstance())
    assertBleState(getDevice(patchedResp.getDevicesList(), name), false)

    // Turn on Radio State (BLE) and verify.
    NetsimController.defaultDeadline().patchDevice(patchBleStateRequest(name, true))

    patchedResp = NetsimController.defaultDeadline().listDevice(Empty.getDefaultInstance())
    assertBleState(getDevice(patchedResp.getDevicesList(), name), true)

    // Turn off Radio State (BLE), reset and verify.
    NetsimController.defaultDeadline().patchDevice(patchBleStateRequest(name, false))
    NetsimController.defaultDeadline().reset(Empty.getDefaultInstance())

    patchedResp = NetsimController.defaultDeadline().listDevice(Empty.getDefaultInstance())
    assertBleState(getDevice(patchedResp.getDevicesList(), name), true)
  }
}

private const val DEVICE_ATTACH_TIMEOUT_MS = 5_000L
private const val DEVICE_ATTACH_POLL_INTERVAL_MS = 200L

fun hasNonBeaconBluetoothChip(device: Device): Boolean {
  return device.getChipsList().any { it.getKind() == ChipKind.BLUETOOTH && it.hasBt() }
}

fun waitForBluetoothDeviceName(): String {
  val deadlineNs = System.nanoTime() + DEVICE_ATTACH_TIMEOUT_MS * 1_000_000L
  var lastDevices: List<Device> = emptyList()
  while (true) {
    val resp = NetsimController.defaultDeadline().listDevice(Empty.getDefaultInstance())
    lastDevices = resp.getDevicesList()
    val btDevice = lastDevices.firstOrNull(::hasNonBeaconBluetoothChip)
    if (btDevice != null) {
      return btDevice.getName()
    }
    if (System.nanoTime() >= deadlineNs) {
      break
    }
    Thread.sleep(DEVICE_ATTACH_POLL_INTERVAL_MS)
  }
  val seenNames = lastDevices.map { it.getName() }
  Assert.fail(
    "Timed out after ${DEVICE_ATTACH_TIMEOUT_MS} ms waiting for a non-beacon Bluetooth device in netsimd; saw devices: $seenNames"
  )
  return ""
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
  val btChips =
    device.getChipsList().filter { it.getKind() == ChipKind.BLUETOOTH && it.hasBt() }
  Assert.assertFalse(
    "Expected device '${device.getName()}' to have a non-beacon Bluetooth chip, found chips: ${device.getChipsList()}",
    btChips.isEmpty(),
  )
  for (chip in btChips) {
    Assert.assertEquals(
      "Unexpected BLE radio state for device '${device.getName()}'",
      state,
      chip.getBt().getLowEnergy().getState(),
    )
  }
}
