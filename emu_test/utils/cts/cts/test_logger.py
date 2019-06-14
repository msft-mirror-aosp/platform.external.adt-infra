"""Contains a TestLogger that can be used to log cts results."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import base64
import sys
import time

from absl.testing import absltest
from lxml import etree as ET
from absl import logging


class Timer(object):
  """A very simple timer that tracks time passed in ms."""

  def __init__(self):
    self.start()

  def start(self):
    self.timer = time.time()

  def time(self):
    return int((time.time() - self.timer) * 1000)


class CtsTestLogger(object):
  """Produces a test.xml log that sponge understands.

    Does support multiple testsuites. This is really used to translate
    and track the results from the Cts run.

    See
    http://cs/search?q=class%3Acom.google.testing.util.XMLResultFormatter%24
    for details.
  """

  def __init__(self, fn=None, always_write=True, timer=Timer()):
    """Creates a logger that produces XML files that can be consumed by sponge.

    Args:
      fn: File object to write the test suite xml to. If this is None
          it will default to Test.xml that sponge can find.
      always_write: True if write Test.xml after every method call
          this will increase the likleyhood of a Test.xml being present in case
          of timeouts. Note that this can be very costly!
       timer: Timer to use to measer elapsed time.
    """
    self.file = None
    if fn:
      self.file = fn

    self.always_write = always_write
    self.root = ET.Element('testsuites')
    self.suite = ET.SubElement(self.root, 'testsuite')
    self.sw = timer
    self.module = None
    self.expect = []

  def _update(self):
    if self.always_write:
      self.write()
      self.file.seek(0)

  def _completed(self, name, ms):
    """Marks the given name as completed.

    Args:
      name: The name of the test
      ms: The runtime of the test.
    Returns:
      The created xml subelement.
    """
    # Remove the skip element if this name is matching
    # It will be re-added if needed
    for test in self.suite:
      if test.get('name') == name:
        if len(test) > 0 and test[0].tag in ['skipped', 'failure']:
          self.suite.remove(test)
        else:
          return ET.Element('Unused')

    test = ET.SubElement(self.suite, 'testcase')
    test.set('name', name)
    test.set('status', 'run')
    test.set('result', 'completed')
    test.set('time', str(int(ms)))
    test.set('classname', '')
    self.sw.start()
    return test

  def start(self, module, count=0, expect=None):
    """Marks the start of this module.

    It immediately marks all tests in expect as skipped.

    Args:
      module: The name of the module.
      count: The number of tests to be run.
      expect: The set of tests that we expect to execute.
    """
    logging.info('Starting module: %s, with %d tests', module, count)
    if self.suite.get('name') != module:
      self.sw.start()
    self.suite.set('name', module)
    self.suite.set('tests', str(count))
    self._update()
    self.expect = expect or []
    for e in self.expect:
      self.skip(e, 'not yet run')

  def success(self, test, ms=0):
    ms = ms or self.sw.time()
    logging.info('Test: %s, succeeded  in: %d ms', test, ms)
    self._completed(test, ms)
    self._update()

  def fail(self, test, error, ms=0):
    """Log a failed test."""
    ms = ms or self.sw.time()
    logging.info('Test: %s, failed in: %d ms, with: %s', test, ms, error)
    entry = self._completed(test, ms)
    failure = ET.SubElement(entry, 'failure')
    failure.set('message', 'Failure')
    failure.text = ET.CDATA(error)
    self._update()

  def skip(self, test, msg, ms=0):
    ms = ms or self.sw.time()
    logging.warn('Test: %s, skipped in: %d ms', test, ms)
    entry = self._completed(test, ms)
    failure = ET.SubElement(entry, 'skipped')
    failure.set('type', 'unittest.case.SkipTest')
    failure.text = ET.CDATA(msg)
    self._update()

  def done(self, success, fail, ms=0):
    ms = ms or self.sw.time()
    self.suite.set('failures', str(fail))
    self.suite.set('success', str(success))
    self.suite.set('errors', '0')
    self.suite.set('time', str(int(ms)))
    self.suite = ET.SubElement(self.root, 'testsuite')
    self._update()

  def from_json(self, test):
    """Creates a success/skip or failure node based on the json report.

    The json report from a CTS run can be fed to the logger to create the
    proper XML entries.

    Args:
        test: The json reported by the CTS JsonReporter.
    """
    state = test['status']
    ms = test['time']

    if state == 'Start':
      self.start(test['module'], test['total'])
    elif state == 'Done':
      self.done(test['success'], test['failed'])
      return
    elif state == 'Pass':
      self.success(test['test'], ms)
    elif state == 'Skip':
      self.skip(test['test'],
                base64.b64decode(test['trace']).decode('utf8'), ms)
    else:
      self.fail(test['test'],
                base64.b64decode(test['trace']).decode('utf8'), ms)

  def write(self):
    """Persists the current xml state.

    If no file has been set it will try to open the default xml output.
    If this fails the xml will be written to stderr.
    """
    if not self.file:
        self.file = sys.stderr

    self.file.write(ET.tostring(self.root))
    self.file.truncate()
    self.file.flush()
