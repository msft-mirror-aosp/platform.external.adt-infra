"""Tests for port-related commands."""

import inspect
import time
import unittest

from . import testcase_base
from .utils import util

EMULATOR_PORT = '5554'
HOST_PORT = '5556'

CMD_REDIR_LIST = 'redir list\n'
CMD_REDIR_ADD = 'redir add tcp:%s:%s\n' % (HOST_PORT, EMULATOR_PORT)
CMD_REDIR_DEL = 'redir del tcp:%s\n' % HOST_PORT


class PortTest(testcase_base.BaseConsoleTest):
  """This class aims to test redir-related emulator console commands."""

  def __init__(self, method_name=None):
    if method_name:
      super(PortTest, self).__init__(method_name)
    else:
      super(PortTest, self).__init__()

  def _list_redir_cmd(self):
    is_cmd_succ, output_redir_list = util.execute_console_command(
        self.telnet, CMD_REDIR_LIST, util.PORT_NO_REDIR)
    self.assert_cmd_successful(
        is_cmd_succ, 'Failed to properly list port redirection.',
        False, '', util.PORT_NO_REDIR, output_redir_list)
    return output_redir_list

  def _add_port_redir_cmd(self):
    is_cmd_succ, output_redir_add = util.execute_console_command(
        self.telnet, CMD_REDIR_ADD, util.OK)
    self.assert_cmd_successful(
        is_cmd_succ, 'Failed to properly add port redirection.',
        False, '', util.OK, output_redir_add)

    is_cmd_succ, output_redir_list = util.execute_console_command(
        self.telnet, CMD_REDIR_LIST, util.PORT_REDIR_ADD)
    self.assert_cmd_successful(
        is_cmd_succ, 'Failed to properly list port redirection.',
        False, '', util.PORT_REDIR_ADD, output_redir_list)

  def _del_port_redir_cmd(self):

    is_cmd_succ, output_redir_del = util.execute_console_command(
        self.telnet, CMD_REDIR_DEL, util.OK)
    self.assert_cmd_successful(
        is_cmd_succ, 'Failed to properly delete port redirection.',
        False, '', util.OK, output_redir_del)

  def test_list_port_redir(self):
    """Test for command: redir list.

    TT ID: fa2c6127-83e8-4f36-b5d9-8f87b42ed8eb
    """
    print(('Running test: %s' % (inspect.stack()[0][3])))
    self._list_redir_cmd()

  def test_add_new_port_and_delete_port_redir(self):
    """Test for commands: redir.

    redir add <tcp_or_udp>:<5556>:<port_of_emulator>
    redir def <tcp_or_udp>:<5556>
    TT ID: fa2c6127-83e8-4f36-b5d9-8f87b42ed8eb
    b/210442:
      command "redir del" doesn't work on API 23/24 on Windows; but Linux.
    """
    print(('Running test: %s' % (inspect.stack()[0][3])))
    self._add_port_redir_cmd()
    self._del_port_redir_cmd()


if __name__ == '__main__':
  print('======= Port Test =======')
  unittest.main()
