package com.android.tools.e2etests.sensors

import android.content.Context
import android.location.Location
import android.location.LocationManager
import androidx.test.platform.app.InstrumentationRegistry
import com.android.emulator.control.GpsState
import com.android.emulator.control.ParameterValue
import com.android.emulator.control.SensorValue
import com.android.tools.e2etests.grpc.EmulatorController
import com.google.protobuf.Empty
import com.google.testing.junit.testparameterinjector.TestParameter
import com.google.testing.junit.testparameterinjector.TestParameterInjector
import org.junit.Assert
import org.junit.Test
import org.junit.runner.RunWith

val TOLERANCE = 0.0002f

@RunWith(TestParameterInjector::class)
class SensorTest {

  enum class TestCase(val target: SensorValue.SensorType, val value: List<Float>) {
    GYROSCOPE(SensorValue.SensorType.GYROSCOPE, listOf(1f, 1f, 1f)),
    MAGNETIC_FIELD(SensorValue.SensorType.MAGNETIC_FIELD, listOf(21f, 1f, 40f)),
    ORIENTATION(SensorValue.SensorType.ORIENTATION, listOf(90f, 0f, 0f)),
    TEMPERATURE(SensorValue.SensorType.TEMPERATURE, listOf(25f)),
    PROXIMITY(SensorValue.SensorType.PROXIMITY, listOf(5f)),
    LIGHT(SensorValue.SensorType.LIGHT, listOf(10000f)),
    PRESSURE(SensorValue.SensorType.PRESSURE, listOf(100f)),
    HUMIDITY(SensorValue.SensorType.HUMIDITY, listOf(50f)),
    MAGNETIC_FIELD_UNCALIBRATED(
      SensorValue.SensorType.MAGNETIC_FIELD_UNCALIBRATED,
      listOf(20f, 5f, 40f),
    ),
    GYROSCOPE_UNCALIBRATED(SensorValue.SensorType.GYROSCOPE_UNCALIBRATED, listOf(2f, 2f, 2f)),
    ACCELERATION(SensorValue.SensorType.ACCELERATION, listOf(10f, 0f, 0f)),
    ACCELERATION_UNCALIBRATED(SensorValue.SensorType.ACCELERATION_UNCALIBRATED, listOf(25f, 0f, 0f)),
  }

  @Test
  fun setAndGetSensor(@TestParameter testCase: TestCase) {
    EmulatorController.defaultDeadline()
      .setSensor(
        SensorValue.newBuilder()
          .setTarget(testCase.target)
          .setValue(ParameterValue.newBuilder().addAllData(testCase.value).build())
          .build()
      )

    for (i in 1..5) {
      if (sensorValueMatches(testCase.target, testCase.value)) {
        return
      }
      Thread.sleep(100)
    }

    Assert.fail("Sensor value never stabilized")
  }

  fun sensorValueMatches(target: SensorValue.SensorType, value: List<Float>): Boolean {
    val resp =
      EmulatorController.defaultDeadline()
        .getSensor(SensorValue.newBuilder().setTarget(target).build())

    Assert.assertEquals(resp.getTarget(), target)

    if (resp.getValue().getDataCount() != value.size) {
      return false
    }
    for ((i, got) in resp.getValue().getDataList().withIndex()) {
      if (!approxEqual(got, value[i])) {
        return false
      }
    }
    return true
  }

  enum class GpsTestCase(val latitude: Double, val longitude: Double, val altitude: Double) {
    SANTA_CRUZ(37.0, -122.0, 11.0),
    TRISTAN_DA_CUNHA(37.0, 12.0, 2.0),
  }

  @Test
  fun setAndGetGps(@TestParameter testCase: GpsTestCase) {
    EmulatorController.defaultDeadline()
      .setGps(
        GpsState.newBuilder()
          .setLatitude(testCase.latitude)
          .setLongitude(testCase.longitude)
          .setAltitude(testCase.altitude)
          .build()
      )

    var matched = false
    for (i in 1..5) {
      if (gpsGrpcValueMatches(testCase)) {
        matched = true
      }
      Thread.sleep(100)
    }

    Assert.assertTrue("GPS grpc response never stabilized", matched)

    matched = false
    for (i in 1..5) {
      if (gpsAndroidValueMatches(testCase)) {
        matched = true
      }
      Thread.sleep(100)
    }
  }

  fun gpsGrpcValueMatches(want: GpsTestCase): Boolean {
    val resp = EmulatorController.defaultDeadline().getGps(Empty.getDefaultInstance())
    return approxEqual(resp.getLatitude(), want.latitude) &&
      approxEqual(resp.getLongitude(), want.longitude) &&
      approxEqual(resp.getAltitude(), want.altitude)
  }

  fun gpsAndroidValueMatches(want: GpsTestCase): Boolean {
    val context = InstrumentationRegistry.getInstrumentation().targetContext
    val locationManager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
    val location: Location? = locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER)
    return location != null &&
      approxEqual(location.latitude, want.latitude) &&
      approxEqual(location.longitude, want.longitude) &&
      approxEqual(location.altitude, want.altitude)
  }
}

fun approxEqual(a: Double, b: Double): Boolean {
  return Math.abs(a - b) < TOLERANCE
}

fun approxEqual(a: Float, b: Float): Boolean {
  return Math.abs(a - b) < TOLERANCE
}
