"""Test the emulator mttf time"""

import heapq
import os
import psutil
import re
import shutil
import subprocess
import time
import time
import traceback
import unittest

try:
  import asyncio
except ImportError:
  import trollius as asyncio

from emu_test.utils.emu_error import TimeoutError
from emu_test.utils.emu_argparser import emu_args
import emu_test.utils.emu_testcase
from emu_test.utils.emu_testcase import EmuBaseTestCase, AVDConfig
import emu_test.utils.path_utils as path_utils
from emu_test.test_mttf.emulator_connection import EmulatorConnection
from emu_test.test_mttf.action import *


class MttfTestCase(EmuBaseTestCase):
  """Mean time to failure test.

     This test will just send random clicks to the emulator until it dies.
  """

  def __init__(self, *args, **kwargs):
    super(MttfTestCase, self).__init__(*args, **kwargs)
    self.avd_config = None
    self.mttf_time = time.time()
    self.connection = None

  @classmethod
  def setUpClass(cls):
    super(MttfTestCase, cls).setUpClass()

  def kill_emulator(self):
    self.m_logger.debug('First try - quit emulator by adb emu kill')
    adb_binary = path_utils.get_adb_binary()
    psutil.Popen([adb_binary, 'emu', 'kill']).communicate()
    # check emulator process is terminated
    result = self.term_check(timeout=5)
    if not result:
      self.m_logger.info('Second try - quit emulator by psutil')
      self.kill_proc_by_name(['emulator', 'qemu-system'])
      result = self.term_check(timeout=10)
      self.m_logger.info('term_check after psutil.kill - %s' % result)
    return result

  def tearDown(self):
    result = self.kill_emulator()
    self.m_logger.info('Remove AVD inside of tear down')
    # avd should be found $HOME/.android/avd/
    avd_dir = os.path.join(os.path.expanduser('~'), '.android', 'avd')
    try:
      if result and self.start_proc:
        self.start_proc.wait()
      time.sleep(1)
      self.kill_proc_by_name(['crash-service', 'adb'])
      os.remove(os.path.join(avd_dir, '%s.ini' % self.avd_config.name()))
      shutil.rmtree(
          os.path.join(avd_dir, '%s.avd' % self.avd_config.name()),
          ignore_errors=True)
    except Exception, e:
      self.m_logger.error('Error in cleanup - %r' % e)

  def mttf_check(self, avd):

    @asyncio.coroutine
    def randomizer(connection, actions):
      # Priority queue ordered by when the event should be sent
      # to the emulator.
      heap = []
      tm = time.time()
      for a in actions:
        heapq.heappush(heap, (tm + a.interval, a))

      while connection.is_connected():
        now = time.time()
        evt_time, action = heapq.heappop(heap)
        timeout = evt_time - now

        # Wait until this event is ready to be fired.
        if timeout > 0:
          time.sleep(timeout)

        # Produce the event, if any
        event = action.produce_event()
        if event:
          yield connection.send(event)

        # Schedule it for future execution.
        heapq.heappush(heap, (time.time() + action.interval, action))

    def get_screen_size(adb):
      # this will give something like: 'Physical size: 1080x1920\n'
      screen_info = subprocess.check_output([adb, 'shell', 'wm', 'size'])
      match = re.match('.*: (\d+)x(\d+)', screen_info)
      w = 1080
      h = 1920
      if match:
        w = match.group(1)
        h = match.group(2)
      return w, h

    try:
      self.launch_emu_and_wait(avd)
    except TimeoutError:
      self.m_logger.error('AVD %s, time out, try one more time' % str(avd))
    except:
      self.m_logger.error('AVD %s, exception, try one more time' % str(avd))
      self.m_logger.error(traceback.format_exc())

    adb = path_utils.get_adb_binary()
    w, h = get_screen_size(adb)
    action_set = [
        MouseEvent(w, h),
        SmsEvent(),
        GeoEvent(),
        PowerEvent(),
        ScreenRecord(),
        Sensor(),
        Finger(),
        Snapshot()
    ]
    connection = EmulatorConnection.connect(5554)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(randomizer(connection, action_set))

  def run_mttf_test(self, avd_config):
    pass
    # TODO(jansene): These tests can run for hours/(days?) so are disabled for now
    # self.avd_config = avd_config
    # if self.create_avd(avd_config) == 0:
    #   self.mttf_check(avd_config)


def create_test_case_for_avds():
  pass
  # TODO(jansene): These tests can run for hours/(days?) so are disabled for now
  # create_test_case_from_file("mttf", MttfTestCase, MttfTestCase.run_mttf_test)


if emu_args.config_file is None:
  create_test_case_for_avds()
else:
  emu_test.utils.emu_testcase.create_test_case_from_file(
      'mttf', MttfTestCase, MttfTestCase.run_mttf_test)
