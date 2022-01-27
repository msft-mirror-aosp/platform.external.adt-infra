"""Tests for sensor-related commands."""


from . import testcase_base
from .utils import util
import unittest
import sys

CMD_SENSOR_DISPLAY = 'sensor status\n'

CMD_SENSOR_GET = 'sensor get {}\n'
CMD_SENSOR_SET = 'sensor set {} {}\n'
ASSERT_MSG = 'Failed to {} {} sensor value'

UPDATED_ACCELERATION = '7.55:0.56:6.24'
UPDATED_GYROSCOPE = '1:1:1'
UPDATED_HUMIDITY = '50:0:0'
UPDATED_LIGHT = '10000:0:0'
UPDATED_MAGNETIC_FIELD = '21:1:40'
UPDATED_ORIENTATION = '90:0:0'
UPDATED_PRESSURE = '100:0:0'
UPDATED_PROXIMITY = '5:0:0'
UPDATED_TEMPERATURE = '25:0:0'
UPDATED_UNCALIBRATED_GYROSCOPE = '2:2:2'
UPDATED_UNCALIBRATED_MAGNETIC_FIELD = '20:5:40'

RETRIEVED_HUMIDITY = '50'
RETRIEVED_LIGHT = '10000'
RETRIEVED_PRESSURE = '100'
RETRIEVED_PROXIMITY = '5'
RETRIEVED_TEMPERATURE = '25'

MAGNETIC_FIELD = 'magnetic-field'
UNCALIBRATED_MAGNETIC_FIELD = 'magnetic-field-uncalibrated'
UNCALIBRATED_GYROSCOPE = 'gyroscope-uncalibrated'
ACCELERATION = 'acceleration'
GYROSCOPE = 'gyroscope'
TEMPERATURE = 'temperature'
LIGHT = 'light'
ORIENTATION = 'orientation'
PRESSURE = 'pressure'
PROXIMITY = 'proximity'
HUMIDITY = 'humidity'
REGEX_SENSOR_DISPLAY = 'acceleration:.*\ngyroscope:.*\nmagnetic-field:.*' \
                       '\norientation:.*\ntemperature:.*\nproximity:.*\nlight:.*' \
                       '\npressure:.*\nhumidity:.*\nmagnetic-field-uncalibrated:.*\ngyroscope-uncalibrated'

PREFIX_SET = 'set'
PREFIX_GET = 'get'


class SensorTest(testcase_base.BaseConsoleTest):
  """Tests for sensor-related commands."""

  def __init__(self, method_name=None):
    if method_name:
      super(SensorTest, self).__init__(method_name)
    else:
      super(SensorTest, self).__init__()

  def test_magnetic_field_sensor(self):
    """Test for command: sensor set magnetic-field <value>.

    TT ID: 4e652d61-4862-4a8f-9d8b-0329847d1cfb
    Test steps:
      1. Run: sensor set magnetic-field <value>
      2. Check that the set command returned OK.
      3. Run: sensor get magnetic-field
      4. Check that the retrieved value is same as the set value.

    Verify:
      1. Emulator displays magnetic-field values as <value>
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    self._execute_command_and_verify(CMD_SENSOR_SET.format(MAGNETIC_FIELD, UPDATED_MAGNETIC_FIELD), util.OK,
                                     ASSERT_MSG.format(PREFIX_SET, MAGNETIC_FIELD))
    self._execute_command_and_verify(CMD_SENSOR_GET.format(MAGNETIC_FIELD), UPDATED_MAGNETIC_FIELD,
                                     ASSERT_MSG.format(PREFIX_GET, MAGNETIC_FIELD))

  def test_acceleration_sensor(self):
    """Test for command: sensor set acceleration <value>.

    TT ID: 4e652d61-4862-4a8f-9d8b-0329847d1cfb
    Test steps:
      1. Run: sensor set acceleration <value>
      2. Check that the set command returned OK.
      3. Run: sensor get acceleration
      4. Check that the retrieved value is same as the set value.

    Verify:
      1. Emulator displays acceleration values as <value>
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    self._execute_command_and_verify(CMD_SENSOR_SET.format(ACCELERATION,
                                     UPDATED_ACCELERATION), util.OK, ASSERT_MSG.format(PREFIX_SET, ACCELERATION))
    self._execute_command_and_verify(CMD_SENSOR_GET.format(ACCELERATION), UPDATED_ACCELERATION,
                                     ASSERT_MSG.format(PREFIX_GET, ACCELERATION))

  def test_gyroscope_sensor(self):
    """Test for command: sensor set gyroscope <value>.

    TT ID: 4e652d61-4862-4a8f-9d8b-0329847d1cfb
    Test steps:
      1. Run: sensor set gyroscope <value>
      2. Check that the set command returned OK.
      3. Run: sensor get gyroscope
      4. Check that the retrieved value is same as the set value.

    Verify:
      1. Emulator displays gyroscope values as <value>
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    self._execute_command_and_verify(CMD_SENSOR_SET.format(GYROSCOPE, UPDATED_GYROSCOPE), util.OK,
                                     ASSERT_MSG.format(PREFIX_SET, GYROSCOPE))
    self._execute_command_and_verify(CMD_SENSOR_GET.format(GYROSCOPE), UPDATED_GYROSCOPE,
                                     ASSERT_MSG.format(PREFIX_GET, GYROSCOPE))

  def test_orientation_sensor(self):
    """Test for command: sensor set orientation <value>.

    TT ID: 4e652d61-4862-4a8f-9d8b-0329847d1cfb
    Test steps:
      1. Run: sensor set orientation <value>
      2. Check that the set command returned OK.
      3. Run: sensor get orientation
      4. Check that the retrieved value is same as the set value.

    Verify:
      1. Emulator displays orientation values as <value>
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    self._execute_command_and_verify(CMD_SENSOR_SET.format(ORIENTATION, UPDATED_ORIENTATION), util.OK,
                                     ASSERT_MSG.format(PREFIX_SET, ORIENTATION))
    self._execute_command_and_verify(CMD_SENSOR_GET.format(ORIENTATION), UPDATED_ORIENTATION,
                                     ASSERT_MSG.format(PREFIX_GET, ORIENTATION))

  def test_temperature_sensor(self):
    """Test for command: sensor set temperature <value>.

    TT ID: 4e652d61-4862-4a8f-9d8b-0329847d1cfb
    Test steps:
      1. Run: sensor set temperature <value>
      2. Check that the set command returned OK.
      3. Run: sensor get temperature
      4. Check that the retrieved value is same as the set value.

    Verify:
      1. Emulator displays temperature values as <value>
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    self._execute_command_and_verify(CMD_SENSOR_SET.format(TEMPERATURE, UPDATED_TEMPERATURE), util.OK,
                                     ASSERT_MSG.format(PREFIX_SET, TEMPERATURE))
    self._execute_command_and_verify(CMD_SENSOR_GET.format(TEMPERATURE), RETRIEVED_TEMPERATURE,
                                     ASSERT_MSG.format(PREFIX_GET, TEMPERATURE))

  def test_light_sensor(self):
    """Test for command: sensor set light <value>.

    TT ID: 4e652d61-4862-4a8f-9d8b-0329847d1cfb
    Test steps:
      1. Run: sensor set light <value>
      2. Check that the set command returned OK.
      3. Run: sensor get light
      4. Check that the retrieved value is same as the set value.

    Verify:
      1. Emulator displays light values as <value>
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    self._execute_command_and_verify(CMD_SENSOR_SET.format(LIGHT, UPDATED_LIGHT), util.OK,
                                     ASSERT_MSG.format(PREFIX_SET, LIGHT))
    self._execute_command_and_verify(CMD_SENSOR_GET.format(LIGHT), RETRIEVED_LIGHT,
                                     ASSERT_MSG.format(PREFIX_GET, LIGHT))

  def test_pressure_sensor(self):
    """Test for command: sensor set pressure <value>.

    TT ID: 4e652d61-4862-4a8f-9d8b-0329847d1cfb
    Test steps:
      1. Run: sensor set pressure <value>
      2. Check that the set command returned OK.
      3. Run: sensor get pressure
      4. Check that the retrieved value is same as the set value.

    Verify:
      1. Emulator displays pressure values as <value>
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    self._execute_command_and_verify(CMD_SENSOR_SET.format(PRESSURE, UPDATED_PRESSURE), util.OK,
                                     ASSERT_MSG.format(PREFIX_SET, PRESSURE))
    self._execute_command_and_verify(CMD_SENSOR_GET.format(PRESSURE), RETRIEVED_PRESSURE,
                                     ASSERT_MSG.format(PREFIX_GET, PRESSURE))

  def test_proximity_sensor(self):
    """Test for command: sensor set proximity <value>.

    TT ID: 4e652d61-4862-4a8f-9d8b-0329847d1cfb
    Test steps:
      1. Run: sensor set proximity <value>
      2. Check that the set command returned OK.
      3. Run: sensor get proximity
      4. Check that the retrieved value is same as the set value.

    Verify:
      1. Emulator displays proximity values as <value>
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    self._execute_command_and_verify(CMD_SENSOR_SET.format(PROXIMITY, UPDATED_PROXIMITY), util.OK,
                                     ASSERT_MSG.format(PREFIX_SET, PROXIMITY))
    self._execute_command_and_verify(CMD_SENSOR_GET.format(PROXIMITY), RETRIEVED_PROXIMITY,
                                     ASSERT_MSG.format(PREFIX_GET, PROXIMITY))

  def test_humidity_sensor(self):
    """Test for command: sensor set humidity <value>.

    TT ID: 4e652d61-4862-4a8f-9d8b-0329847d1cfb
    Test steps:
      1. Run: sensor set humidity <value>
      2. Check that the set command returned OK.
      3. Run: sensor get humidity
      4. Check that the retrieved value is same as the set value.

    Verify:
      1. Emulator displays humidity values as <value>
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    self._execute_command_and_verify(CMD_SENSOR_SET.format(HUMIDITY, UPDATED_HUMIDITY), util.OK,
                                     ASSERT_MSG.format(PREFIX_SET, HUMIDITY))
    self._execute_command_and_verify(CMD_SENSOR_GET.format(HUMIDITY), RETRIEVED_HUMIDITY,
                                     ASSERT_MSG.format(PREFIX_GET, HUMIDITY))

  def test_magnetic_field_uncalibrated_sensor(self):
    """Test for command: sensor set magnetic_field_uncalibrated <value>.

    TT ID: 4e652d61-4862-4a8f-9d8b-0329847d1cfb
    Test steps:
      1. Run: sensor set magnetic-field-uncalibrated <value>
      2. Check that the set command returned OK.
      3. Run: sensor get magnetic-field-uncalibrated
      4. Check that the retrieved value is same as the set value.

    Verify:
      1. Emulator displays magnetic_field_uncalibrated values as <value>
   """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    self._execute_command_and_verify(CMD_SENSOR_SET.format(UNCALIBRATED_MAGNETIC_FIELD, UPDATED_UNCALIBRATED_MAGNETIC_FIELD), util.OK,
                                     ASSERT_MSG.format(PREFIX_SET, UNCALIBRATED_MAGNETIC_FIELD))
    self._execute_command_and_verify(CMD_SENSOR_GET.format(UNCALIBRATED_MAGNETIC_FIELD), UPDATED_UNCALIBRATED_MAGNETIC_FIELD,
                                     ASSERT_MSG.format(PREFIX_GET, UNCALIBRATED_MAGNETIC_FIELD))

  def test_gyroscope_uncalibrated_sensor(self):
    """Test for command: sensor set gyroscope_uncalibrated <value>.

    TT ID: 4e652d61-4862-4a8f-9d8b-0329847d1cfb
    Test steps:
      1. Run: sensor set gyroscope-uncalibrated <value>
      2. Check that the set command returned OK.
      3. Run: sensor get gyroscope-uncalibrated
      4. Check that the retrieved value is same as the set value.

    Verify:
      1. Emulator displays gyroscope_uncalibrated values as <value>
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    self._execute_command_and_verify(
      CMD_SENSOR_SET.format(UNCALIBRATED_GYROSCOPE, UPDATED_UNCALIBRATED_GYROSCOPE), util.OK,
      ASSERT_MSG.format(PREFIX_SET, UNCALIBRATED_GYROSCOPE))
    self._execute_command_and_verify(CMD_SENSOR_GET.format(UNCALIBRATED_GYROSCOPE),
                                     UPDATED_UNCALIBRATED_GYROSCOPE,
                                     ASSERT_MSG.format(PREFIX_GET, UNCALIBRATED_GYROSCOPE))

  def _execute_command_and_verify(self, command, expected_output, assert_msg):
    """Executes console command and verify output.

    Args:
      command: Console command to be executed.
      expected_output: Expected console output.
      assert_msg: Assertion message.
    """
    is_command_successful, output = util.execute_console_command(
      self.telnet, command, expected_output)
    self.assert_cmd_successful(is_command_successful, assert_msg, False, '',
                               'Pattern: \n%s' % expected_output, output)

  def test_sensor_display(self):
    """Test for command: sensor status <value>.

    TT ID: 4e652d61-4862-4a8f-9d8b-0329847d1cfb
    Test steps:
      1. Run: sensor status, and Verify 1

    Verify:
      1. Emulator displays all the sensors with status enabled/disabled
    """
    this_function_name = sys._getframe().f_code.co_name
    print(('Running test: %s' % (this_function_name)))
    assert_msg = 'Failed to properly display sensor details.'
    self._execute_command_and_verify(CMD_SENSOR_DISPLAY,
                                     REGEX_SENSOR_DISPLAY,
                                     assert_msg)


if __name__ == '__main__':
  print('======= Sensor Test =======')
  unittest.main()