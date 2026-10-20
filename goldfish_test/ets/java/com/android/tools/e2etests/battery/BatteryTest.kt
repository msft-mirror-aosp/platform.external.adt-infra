package com.android.tools.e2etests.battery

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import androidx.test.platform.app.InstrumentationRegistry
import com.android.emulator.control.BatteryState
import com.android.tools.e2etests.grpc.EmulatorController
import com.google.protobuf.Empty
import com.google.testing.junit.testparameterinjector.TestParameter
import com.google.testing.junit.testparameterinjector.TestParameterInjector
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import org.junit.Assert
import org.junit.Test
import org.junit.runner.RunWith

val hasBattery = true

val healthMap =
  mapOf(
    BatteryState.BatteryHealth.GOOD to BatteryManager.BATTERY_HEALTH_GOOD,
    BatteryState.BatteryHealth.FAILED to BatteryManager.BATTERY_HEALTH_UNSPECIFIED_FAILURE,
    BatteryState.BatteryHealth.DEAD to BatteryManager.BATTERY_HEALTH_DEAD,
    BatteryState.BatteryHealth.OVERVOLTAGE to BatteryManager.BATTERY_HEALTH_OVER_VOLTAGE,
    BatteryState.BatteryHealth.OVERHEATED to BatteryManager.BATTERY_HEALTH_OVERHEAT,
  )

val statusMap =
  mapOf(
    BatteryState.BatteryStatus.UNKNOWN to BatteryManager.BATTERY_STATUS_UNKNOWN,
    BatteryState.BatteryStatus.CHARGING to BatteryManager.BATTERY_STATUS_CHARGING,
    BatteryState.BatteryStatus.DISCHARGING to BatteryManager.BATTERY_STATUS_DISCHARGING,
    BatteryState.BatteryStatus.NOT_CHARGING to BatteryManager.BATTERY_STATUS_NOT_CHARGING,
    BatteryState.BatteryStatus.FULL to BatteryManager.BATTERY_STATUS_FULL,
  )

// TODO(b/532197553): All chargers show up as AC in android.
val pluggedMap =
  mapOf(
    BatteryState.BatteryCharger.NONE to 0,
    BatteryState.BatteryCharger.AC to BatteryManager.BATTERY_PLUGGED_AC,
    BatteryState.BatteryCharger.USB to BatteryManager.BATTERY_PLUGGED_AC,
    BatteryState.BatteryCharger.WIRELESS to BatteryManager.BATTERY_PLUGGED_AC,
  )

data class AndroidBattery(
  val level: Int,
  val health: Int,
  val status: Int,
  val isPresent: Boolean,
  val plugged: Int,
)

@RunWith(TestParameterInjector::class)
class BatteryTest {

  enum class TestCase(
    val status: BatteryState.BatteryStatus,
    val health: BatteryState.BatteryHealth,
    val charger: BatteryState.BatteryCharger,
    val isPresent: Boolean,
    val chargeLevel: Int,
  ) {
    UNKNOWN_FAILED(
      BatteryState.BatteryStatus.UNKNOWN,
      BatteryState.BatteryHealth.FAILED,
      BatteryState.BatteryCharger.NONE,
      false,
      0,
    ),
    DISCHARGING_DEAD(
      BatteryState.BatteryStatus.DISCHARGING,
      BatteryState.BatteryHealth.DEAD,
      BatteryState.BatteryCharger.NONE,
      true,
      1,
    ),
    NOTCHARGING_OVERVOLTAGE(
      BatteryState.BatteryStatus.NOT_CHARGING,
      BatteryState.BatteryHealth.OVERVOLTAGE,
      BatteryState.BatteryCharger.AC,
      true,
      100,
    ),
    DISCHARGING_OVERHEATED(
      BatteryState.BatteryStatus.DISCHARGING,
      BatteryState.BatteryHealth.OVERHEATED,
      BatteryState.BatteryCharger.NONE,
      true,
      90,
    ),
    CHARGING_GOOD(
      BatteryState.BatteryStatus.CHARGING,
      BatteryState.BatteryHealth.GOOD,
      BatteryState.BatteryCharger.WIRELESS,
      true,
      12,
    ),
    FULL_GOOD(
      BatteryState.BatteryStatus.FULL,
      BatteryState.BatteryHealth.GOOD,
      BatteryState.BatteryCharger.USB,
      true,
      100,
    ),
  }

  @Test
  fun setAndGetBattery(@TestParameter testCase: TestCase) {
      // The Android side battery status is updated via a broadcast receiver.
      // This code will get one immediate update, followed by another then the grpc call is made.
      val latch = CountDownLatch(2)
      var androidBattery: AndroidBattery? = null
      val batteryReceiver =
        object : BroadcastReceiver() {
          override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == Intent.ACTION_BATTERY_CHANGED) {
              val level: Int = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
              val health: Int = intent.getIntExtra(BatteryManager.EXTRA_HEALTH, -1)
              val status: Int = intent.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
              val isPresent: Boolean = intent.getBooleanExtra(BatteryManager.EXTRA_PRESENT, false)
              val plugged: Int = intent.getIntExtra(BatteryManager.EXTRA_PLUGGED, -1)
              androidBattery = AndroidBattery(level, health, status, isPresent, plugged)
              latch.countDown()
            }
          }
        }

      val context = InstrumentationRegistry.getInstrumentation().targetContext
      context.registerReceiver(batteryReceiver, IntentFilter(Intent.ACTION_BATTERY_CHANGED))

      EmulatorController.defaultDeadline()
        .setBattery(
          BatteryState.newBuilder()
            .setStatus(testCase.status)
            .setHealth(testCase.health)
            .setCharger(testCase.charger)
            .setHasBattery(hasBattery)
            .setIsPresent(testCase.isPresent)
            .setChargeLevel(testCase.chargeLevel)
            .build()
        )

      val resp = EmulatorController.defaultDeadline().getBattery(Empty.getDefaultInstance())
      Assert.assertEquals(testCase.status, resp.getStatus())
      Assert.assertEquals(testCase.health, resp.getHealth())
      Assert.assertEquals(hasBattery, resp.getHasBattery())
      Assert.assertEquals(testCase.isPresent, resp.getIsPresent())
      Assert.assertEquals(testCase.chargeLevel, resp.getChargeLevel())

      val success = latch.await(5, TimeUnit.SECONDS)
      Assert.assertTrue("Timed out waiting for battery receiver", success)

      if (androidBattery != null) {
        Assert.assertEquals(testCase.chargeLevel, androidBattery.level)
        Assert.assertEquals(healthMap[testCase.health], androidBattery.health)
        Assert.assertEquals(statusMap[testCase.status], androidBattery.status)
        Assert.assertEquals(testCase.isPresent, androidBattery.isPresent)
        Assert.assertEquals(pluggedMap[testCase.charger], androidBattery.plugged)
      }
    }
}
