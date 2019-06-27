"""This class is a parent class for all subordniate "testcase_" classes.

This class is a parent class for all subordniate "testcase_" classes.
"""

import unittest
import emu_test.utils.path_utils as path_utils

class BaseAdbTest(unittest.TestCase):
  """This is the base clase for fall adb test."""

  def __init__(self, method_name=None, avd=None):
    if method_name:
      super(BaseAdbTest, self).__init__(method_name)
    else:
      super(BaseAdbTest, self).__init__()
    self.avd = avd
    self.adb_binary = path_utils.get_adb_binary()

  def setUp(self):
    print ('Start ADB Test')

  def tearDown(self):
    print ('End ADB Test')

if __name__ == '__main__':
  print '======= Base Console Test ======='
  unittest.main()
