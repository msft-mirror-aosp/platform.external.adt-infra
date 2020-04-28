"""Test for snapshot-related emulator console commands."""

import unittest
import testcase_base
from utils import util
import time
import subprocess
import emu_test.utils.path_utils as path_utils

import sys
sys.path.append("..")

CMD_AVD_SNAPSHOT_SAVE = 'avd snapshot save '
CMD_AVD_SNAPSHOT_LOAD = 'avd snapshot load '
CMD_AVD_SNAPSHOT_LIST = 'avd snapshot list\n'
CMD_AVD_SNAPSHOT_DEL = 'avd snapshot del '
SNAPSHOT_PREFIX = 'snapshot_'
EMPTY_LIST_MSG = 'There is no snapshot available.'
NEW_LINE_COMMAND = '\n'


class SnapshotTest(testcase_base.BaseConsoleTest):
  """This class aims to test snapshot-related emulator console commands."""

  def __init__(self, method_name=None):
    if method_name:
      super(SnapshotTest, self).__init__(method_name)
    else:
      super(SnapshotTest, self).__init__()

  def test_avd_snapshot_save(self):
    """Verifies snapshot command save, returns OK.

    This command is used to save the current state of the running AVD.

    TT ID: b17963d1-5637-49d8-933e-3ec99ce2dee3
    Test steps:
      1. Check if snapshot exist.
      2. Delete the snapshot if already exist.
      3. Save the snapshot.
      4. Check if snapshot above created exist now.
      5. Delete the snapshot created in the test.

    Verify:
      1. Verify that the retrieved snapshot name is the same that was saved.
    """
    this_function_name = sys._getframe().f_code.co_name
    print 'Running test: %s' % (this_function_name)
    snapshot_string = SNAPSHOT_PREFIX + this_function_name
    if util.execute_console_command(self.telnet, CMD_AVD_SNAPSHOT_LIST, snapshot_string) is True:
      self._execute_console_command_and_verify(CMD_AVD_SNAPSHOT_DEL + snapshot_string + NEW_LINE_COMMAND, util.OK)

    self._execute_console_command_and_verify(CMD_AVD_SNAPSHOT_SAVE + snapshot_string + NEW_LINE_COMMAND, util.OK)
    self._execute_console_command_and_verify(CMD_AVD_SNAPSHOT_LIST, snapshot_string)
    self._execute_console_command_and_verify(CMD_AVD_SNAPSHOT_DEL + snapshot_string + NEW_LINE_COMMAND, util.OK)

  def test_avd_snapshot_load(self):
    """Verifies snapshot command load, returns OK.

    This command is used to load an existing snapshot on the AVD.

    TT ID: d2742056-51ae-425c-940e-b770297e95c2
    Test steps:
      1. Launch the Contacts app.
      2. Save a snapshot with Contacts app running.
      3. Load the snapshot created above.
      4. Verify contacts app. is running in the loaded snapshot.
      5. Delete the snapshot created in the test.

    Verify:
      1. Verify contacts app. is running in the loaded snapshot.
    """
    adb_binary = path_utils.get_adb_binary()
    this_function_name = sys._getframe().f_code.co_name
    print 'Running test: %s' % (this_function_name)
    util.launch_application(util.CONTACT_PACKAGE_NAME)
    time.sleep(util.CMD_DELAY_VALUE)
    snapshot_string = SNAPSHOT_PREFIX + this_function_name
    self._execute_console_command_and_verify(CMD_AVD_SNAPSHOT_SAVE + snapshot_string + NEW_LINE_COMMAND, util.OK)
    subprocess.check_output([adb_binary, 'shell', 'am', 'force-stop', util.CONTACT_PACKAGE_NAME])
    time.sleep(util.CMD_DELAY_VALUE)
    self._execute_console_command_and_verify(CMD_AVD_SNAPSHOT_LOAD+snapshot_string+ NEW_LINE_COMMAND, util.OK)
    time.sleep(util.CMD_DELAY_VALUE)
    self.assertTrue(util.check_running_app())
    util.execute_console_command(self.telnet, CMD_AVD_SNAPSHOT_DEL + snapshot_string + NEW_LINE_COMMAND, util.OK)
    subprocess.check_output([adb_binary, 'shell', 'am', 'force-stop', util.CONTACT_PACKAGE_NAME])

  def test_avd_snapshot_del(self):
    """Verifies snapshot command del, returns OK.

    This command is used to delete an existing snapshot.

    TT ID: 78b7fbcc-d3e9-4871-901e-55ab7a200997
    Test steps:
      1. Check if any snapshot exist  , if yes , then delete the snapshot.
      2. Save a new snapshot.
      3. Retrieve the list and check if snapshot created above exist.
      4. If the snapshot exist, then delete it.
      5. Try retrieving the snapshot list.
    Verify:
      1. Verify that output is "There is no snapshot available."
    """
    this_function_name = sys._getframe().f_code.co_name
    print 'Running test: %s' % (this_function_name)
    snapshot_string = SNAPSHOT_PREFIX + this_function_name
    result_execute_list = util.execute_console_command(self.telnet, CMD_AVD_SNAPSHOT_LIST, snapshot_string)
    if result_execute_list[0] is False:
      self._execute_console_command_and_verify(CMD_AVD_SNAPSHOT_SAVE + snapshot_string + NEW_LINE_COMMAND, util.OK)

    util.execute_console_command(self.telnet, CMD_AVD_SNAPSHOT_DEL+snapshot_string+ NEW_LINE_COMMAND, util.OK)
    result_execute_check_snapshot = util.execute_console_command(self.telnet, CMD_AVD_SNAPSHOT_LIST, snapshot_string)
    self.assertFalse(result_execute_check_snapshot[0], "Snapshot "+snapshot_string+" is not deleted successfully.")    #Created snapshot is deleted and no more exist in the retrieved list"

  def test_avd_snapshot_list(self):
    """Verifies snapshot command list, returns OK.

    This command is used to list all the snapshots present on the AVD.

    TT ID:  921ea433-4753-45c9-9cca-03bc7ac5692d
    Test steps:
      1. Save a snapshot.
      2. Retrieve the list and check if snapshot exist
      3. Delete the snapshot created in the test.
    Verify:
      1.  Retrieved list contains the snapshot created.
    """
    this_function_name = sys._getframe().f_code.co_name
    print 'Running test: %s' % (this_function_name)
    snapshot_string = SNAPSHOT_PREFIX + this_function_name
    self._execute_console_command_and_verify(CMD_AVD_SNAPSHOT_SAVE+ snapshot_string +NEW_LINE_COMMAND, util.OK)
    self._execute_console_command_and_verify(CMD_AVD_SNAPSHOT_LIST, snapshot_string)
    util.execute_console_command(self.telnet, CMD_AVD_SNAPSHOT_DEL + snapshot_string + NEW_LINE_COMMAND, util.OK)

  def _execute_console_command_and_verify(self, command, expected_output):
    """Executes emulator console command and verify the command output.

    Args:
      command: Console command to be executed.
      expected_output: The expected command output.
    """
    is_command_successful, output = util.execute_console_command(
        self.telnet, command, expected_output)

    self.assert_cmd_successful(
        is_command_successful, 'Failed to properly execute: %s' % command,
        False, '', expected_output, output)


if __name__ == '__main__':
  print '======= Snapshot Test ======='
  unittest.main()
