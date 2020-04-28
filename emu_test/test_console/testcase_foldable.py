import sys
import unittest
import time
import subprocess
import os
from utils import util
from emu_test.test_console import testcase_base

sys.path.append("..")

CMD_AVD_FOLD = 'fold\n'
CMD_AVD_UNFOLD = 'unfold\n'
CMD_AVD_SNAPSHOT_SAVE = 'avd snapshot save '
CMD_AVD_SNAPSHOT_LOAD = 'avd snapshot load '
SNAPSHOT_PREFIX = 'snapshot_'
CMD_AVD_SNAPSHOT_LIST = 'avd snapshot list\n'
NEW_LINE_COMMAND = '\n'
PREFIX_FOLD = '_fold'
PREFIX_UNFOLD = '_unfold'
ASSERT_MSG_FOLD_FAIL = 'Mismatch in unfold and fold device density, AVD still in unfold state'
ASSERT_MSG_UNFOLD_FAIL = 'Mismatch in unfold and fold device density, AVD still in fold state'
MSG_CMD_FOLD_FAIL = 'Error in folding the AVD'
MSG_CMD_UNFOLD_FAIL = 'Error in unfolding the AVD'


class FoldableTest(testcase_base.BaseConsoleTest):
    """Tests for AVD's with fold feature."""

    def __init__(self, method_name=None):
        if method_name:
            super(FoldableTest, self).__init__(method_name)
        else:
            super(FoldableTest, self).__init__()

    @classmethod
    def setUpClass(cls):
        time.sleep(20)

    @classmethod
    def tearDownClass(cls):
        init, cur = util.get_device_density()
        if init == cur:
            adb_binary = os.path.join(os.environ['ANDROID_SDK_ROOT'], 'platform-tools', 'adb')
            subprocess.check_output([adb_binary, 'emu', CMD_AVD_FOLD])

    def test_fold_feature(self):
      """Verifies fold command, returns OK.

      This command is used to fold  a given AVD.

      TT ID: 392aaede-7819-4d3b-a34c-1b697d3bfd01
      Test steps:
        1. Make sure that the running AVD is in unfolded state.
        2. Execute AVD fold state command .

      Verify:
        1. Verify that unfolded AVD can be folded.
      """
      this_function_name = sys._getframe().f_code.co_name
      print 'Running test: %s' % this_function_name
      init, cur = util.get_device_density()
      if init != cur:
          self._execute_command_and_verify(CMD_AVD_UNFOLD, util.OK, MSG_CMD_UNFOLD_FAIL)
          init, cur = util.get_device_density()
          assert init == cur, ASSERT_MSG_UNFOLD_FAIL

      self._execute_command_and_verify(CMD_AVD_FOLD, util.OK, MSG_CMD_FOLD_FAIL)
      init, cur = util.get_device_density()
      assert init != cur, ASSERT_MSG_FOLD_FAIL

    def test_unfold_feature(self):
      """Verifies unfold command, returns OK.

      This command is used to unfold a given AVD.

      TT ID: 392aaede-7819-4d3b-a34c-1b697d3bfd01
      Test steps:
        1. Make sure that the running AVD is in folded state.
        2. Execute AVD unfold state command .

      Verify:
        1. Verify that folded AVD can be unfolded .
      """
      this_function_name = sys._getframe().f_code.co_name
      print 'Running test: %s' % this_function_name
      init, cur = util.get_device_density()
      if init == cur:
          self._execute_command_and_verify(CMD_AVD_FOLD, util.OK, MSG_CMD_FOLD_FAIL)
          init, cur = util.get_device_density()
          assert init != cur, ASSERT_MSG_FOLD_FAIL

      self._execute_command_and_verify(CMD_AVD_UNFOLD, util.OK, MSG_CMD_UNFOLD_FAIL)
      init, cur = util.get_device_density()
      assert init == cur, ASSERT_MSG_UNFOLD_FAIL

    def test_fold_with_snapshot(self):
      """Verifies snapshot behavior with AVD in fold state.

      This test verifies if snapshot taken from a folded AVD, when loaded,
      makes an unfolded AVD, folded.

      TT ID: 94e86a4b-e90f-445a-8d8d-7182c410a3a2
      Test steps:
        1. Make sure that the running AVD is in folded state.
        2. If not folded, then fold it first.
        3. Save a snapshot .
        4. Unfold the AVD.
        5. Load the snapshot created in step 3.

      Verify:
        1. Verify if snapshot taken from a folded AVD, when loaded,
      makes an unfolded AVD, folded.
      """
      this_function_name = sys._getframe().f_code.co_name
      print 'Running test: %s' % this_function_name
      init, cur = util.get_device_density()
      if init == cur:
          self._execute_command_and_verify(CMD_AVD_FOLD, util.OK, MSG_CMD_FOLD_FAIL)
          init, cur = util.get_device_density()
          assert init != cur, ASSERT_MSG_FOLD_FAIL

      snapshot_string_fold = SNAPSHOT_PREFIX + PREFIX_FOLD
      self._execute_command_and_verify(CMD_AVD_SNAPSHOT_SAVE + snapshot_string_fold + NEW_LINE_COMMAND,
                                     util.OK, 'Error in saving folded snapshot')
      list_snapshots = util.execute_console_command(self.telnet, CMD_AVD_SNAPSHOT_LIST, snapshot_string_fold)
      if list_snapshots[0] is True:
        self.fold_unfold_util(CMD_AVD_UNFOLD, snapshot_string_fold)
        init, cur = util.get_device_density()
        assert init != cur, ASSERT_MSG_FOLD_FAIL

    def test_unfold_with_snapshot(self):
      """Verifies snapshot behavior with AVD in unfold state.

      This test verifies if snapshot taken from a unfolded AVD, when loaded,
      makes an folded AVD, unfolded.

      TT ID: 94e86a4b-e90f-445a-8d8d-7182c410a3a2
      Test steps:
        1. Make sure that the running AVD is in unfolded state.
        2. If not unfolded, then unfold it first.
        3. Save a snapshot .
        4. Fold the AVD.
        5. Load the snapshot created in step 3.

      Verify:
        1. Verify if snapshot taken from a unfolded AVD, when loaded,
      makes an folded AVD, unfolded.
      """
      this_function_name = sys._getframe().f_code.co_name
      print 'Running test: %s' % this_function_name
      init, cur = util.get_device_density()
      if init != cur:
          self._execute_command_and_verify(CMD_AVD_UNFOLD, util.OK, MSG_CMD_UNFOLD_FAIL)
          init, cur = util.get_device_density()
          assert init == cur, ASSERT_MSG_UNFOLD_FAIL

      snapshot_string_unfold = SNAPSHOT_PREFIX + PREFIX_UNFOLD
      self._execute_command_and_verify(CMD_AVD_SNAPSHOT_SAVE + snapshot_string_unfold + NEW_LINE_COMMAND,
                                       util.OK, 'Error in saving unfolded snapshot')
      list_snapshots = util.execute_console_command(self.telnet, CMD_AVD_SNAPSHOT_LIST, snapshot_string_unfold)
      if list_snapshots[0] is True:
          self.fold_unfold_util(CMD_AVD_FOLD, snapshot_string_unfold)
          init, cur = util.get_device_density()
          assert init == cur, ASSERT_MSG_FOLD_FAIL

    def fold_unfold_util(self, device_state, snapshot_name):
        """Folds/unfolds AVD and loads required snapshot.

        Args:
          snapshot_name: Name of the snapshot to be loaded.
          device_state: Current state of AVD. It can be fold OR unfold.
        """
        self._execute_command_and_verify(device_state, util.OK,
                                         'Error in ' + device_state + 'ing the AVD')
        time.sleep(util.CMD_DELAY_VALUE)
        self._execute_command_and_verify(CMD_AVD_SNAPSHOT_LOAD + snapshot_name + NEW_LINE_COMMAND,
                                         util.OK, 'Error in loading ' + device_state + 'ed snapshot')
        time.sleep(util.CMD_DELAY_VALUE)

    def _execute_command_and_verify(self, command, expected_output, assert_msg):
        """Executes console command and verify output.

        Args:
          command: Console command to be executed.
          expected_output: Expected console output.
          assert_msg: Assertion message.
        """
        print 'running command %s' % command
        is_command_successful, output = util.execute_console_command(
            self.telnet, command, expected_output)
        self.assert_cmd_successful(is_command_successful, assert_msg, False, '',
                                   'Pattern: \n%s' % expected_output, output)
        time.sleep(util.CMD_DELAY_VALUE)

if __name__ == '__main__':
    print '======= Foldable Test ======='
    unittest.main()
