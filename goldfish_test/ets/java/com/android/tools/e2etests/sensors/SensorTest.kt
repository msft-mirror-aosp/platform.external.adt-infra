package com.android.tools.e2etests.call

import com.android.emulator.control.ParameterValue
import com.android.emulator.control.SensorValue
import com.android.tools.e2etests.grpc.EmulatorController
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
}

fun approxEqual(a: Float, b: Float): Boolean {
  return Math.abs(a - b) < TOLERANCE
}
