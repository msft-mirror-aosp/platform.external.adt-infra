"""A python 3 ript to run a mean time to failure test.

Mean time to failure is defined as the emulator crashing, not becoming
unresponsive.

We have a list of actions, that have an interval/frequency of when they should
be send to the emulator. When an event is due it is produced (i.e. converted to
a telnet command) and send to the emulator.

It will connect to a running emulator if one is available, otherwise it will
launch one. You must have the 'adb' executable available on the path.

Running against the emulator build in the current branch for example:

 $ python simple_mttf.py --emulator $PWD/../../../qemu/objs/emulator -avd my_avd
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

try:
  from absl import app
  from absl import flags
  from absl import logging
except ImportError:
  print('Make sure to: pip install absl-py')

from action import *
from emulator_connection import EmulatorConnection
import os
import random
import re
import psutil
import subprocess

try:
  import trollius as asyncio
except ImportError:
  print('Make sure to: pip install trollius')

import heapq
import time

FLAGS = flags.FLAGS
flags.DEFINE_string('avd', None,
                    'The avd to test (or pick first available from emulator)')
flags.DEFINE_string(
    'emulator',
    os.path.join(os.environ['ANDROID_SDK_ROOT'], 'emulator', 'emulator'),
    'Emulator executable')
flags.DEFINE_integer('port', 5554, 'Emulator telnet port')
flags.DEFINE_integer('maxboot', 120, 'Maximum time to start emulator')


@asyncio.coroutine
def randomizer(connection, actions):
  # Priority queue ordered by when the event should be sent
  # to the emulator
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
  logging.info('Completed')


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


def get_avd():
  """Just pick the first reported avd from the emulator."""
  return subprocess.check_output([FLAGS.emulator, '-list-avds']).split()[0]


def is_alive():
  """Returns true if the emulator has booted."""
  cmd = ['adb', 'shell', 'getprop', 'sys.boot_completed']
  try:
    return '1' in subprocess.check_output(cmd).decode("utf-8")
  except subprocess.CalledProcessError:
    return False


def launch_emu_and_wait(avd):
  """Super simplistic, poor man's emulator launcher..."""
  cmd = [
      FLAGS.emulator,
      '-avd',
      avd,  # '-verbose', '-show-kernel',
      '-detect-image-hang',
      '-wipe-data',
      '-dns-server',
      '8.8.8.8',
      '-skip-adb-auth'
  ]
  proc = psutil.Popen(cmd)
  max_wait = FLAGS.maxboot
  while (proc.status() not in [
      psutil.STATUS_DEAD, psutil.STATUS_ZOMBIE, psutil.STATUS_STOPPED
  ] and max_wait > 0 and not is_alive()):
    time.sleep(1)
    max_wait = max_wait - 1


def main(argv):
  # launch the emulator if needed
  if not is_alive():
    avd = FLAGS.avd or get_avd()
    launch_emu_and_wait(avd)

  # Get the screen size from the device.
  w, h = get_screen_size('adb')
  # Set of actions we want to send to the emulator
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
  # Connection to the emulator
  connection = EmulatorConnection.connect(FLAGS.port)
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  loop.run_until_complete(randomizer(connection, action_set))


if __name__ == '__main__':
  app.run(main)
