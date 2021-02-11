import os
import platform
import subprocess
import sys
from queue import Queue
from threading import Thread, currentThread
from .cts_log_parser import CtsLogParser
from absl import logging


class CtsRunner(object):
  """A class that can run a cts module, and generate a sponge compatible logging file."""

  def __init__(self, cts, aapt_path, sponge):
    self.cmd = []
    if self.is_windows():
      self.cmd = ['wsl', 'PATH=$PATH:{}'.format(aapt_path)]

    self.cmd += [cts, 'run', 'cts']
    self.test = CtsLogParser(sponge)

  def is_windows(self):
    return platform.system() == 'Windows'

  def _reader(self, pipe, queue):
    try:
      with pipe:
        for line in iter(pipe.readline, b''):
          queue.put((pipe, line[:-1]))
    finally:
      queue.put(None)


  def _log_std_out(self, proc):
    """Logs the output of the given process."""
    q = Queue()
    Thread(target=self._reader, args=[proc.stdout, q]).start()
    Thread(target=self._reader, args=[proc.stderr, q]).start()
    for _ in range(2):
      for _, line in iter(q.get, None):
        self.test.add(line)
        logging.debug(line)

  def _run(self, cmd):
    logging.info('launching: %s', ' '.join(cmd))

    try:
      proc = subprocess.Popen(
          cmd,
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
          shell=self.is_windows(),
      )

      self._log_std_out(proc)
      proc.wait()
      if proc.returncode != 0:
        raise Exception('Failed to run %s - %s' %
                        (' '.join(cmd), proc.returncode))
    finally:
      self.test.flush()


  def run(self, cts):
    test = cts.split(' ')
    suite_test = [x for x in test if x not in ['-t', '-m']]

    self._run(self.cmd + test)
