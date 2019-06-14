"""Tests for  cts_suite.cts_test_runner."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import StringIO
from lxml import etree
from .context import CtsTestLogger

from absl.testing import absltest
from absl import flags

FLAGS = flags.FLAGS


class ZeroTimer(object):

  def __init__(self):
    self.count = 0

  def start(self):
    self.count += 1

  def time(self):
    return self.count


class TestLoggerTest(absltest.TestCase):
  NASTY_STRING = '\nAn unlikeable <xml> & string \n\n\t'

  def setUp(self):
    self.tmp = StringIO.StringIO()
    self.log = CtsTestLogger(self.tmp, timer=ZeroTimer())

  def tearDown(self):
    pass

  def test_can_log(self):
    self.log.start('A', 1)
    self.log.done(1, 1)
    self.log.write()
    self.assertEqual(
        '<testsuites>'
        '<testsuite name="A" tests="1" failures="1"'
        ' success="1" errors="0" time="1"/>'
        '<testsuite/>'
        '</testsuites>', self.tmp.getvalue())

  def test_can_skip(self):
    self.log.skip('A', 'not doing this')
    self.log.done(1, 1)
    self.log.write()
    self.assertEqual(
        '<testsuites>'
        '<testsuite failures="1" success="1" errors="0" time="1">'
        '<testcase name="A" status="run" result="completed" time="0" '
        'classname="">'
        '<skipped type="unittest.case.SkipTest">'
        '<![CDATA[not doing this]]>'
        '</skipped>'
        '</testcase>'
        '</testsuite>'
        '<testsuite/>'
        '</testsuites>', self.tmp.getvalue())

  def test_cdata(self):
    self.log.start('A', 1)
    self.log.fail('test', self.NASTY_STRING)
    self.log.done(1, 1)
    self.log.write()
    root = etree.fromstring(self.tmp.getvalue())
    failure = root.xpath('//failure')
    self.assertTrue(failure)
    self.assertEqual(self.NASTY_STRING, failure[0].text)

  def test_partial_data(self):
    self.log.fail('test', self.NASTY_STRING)
    self.log.write()
    root = etree.fromstring(self.tmp.getvalue())
    failure = root.xpath('//failure')
    self.assertTrue(failure)
    self.assertEqual(self.NASTY_STRING, failure[0].text)

  def test_multiple_suites(self):
    self.log.start('A', 1)
    self.log.done(1, 1)
    self.log.start('B', 2)
    self.log.done(2, 2)
    self.log.write()
    self.assertEqual(
        '<testsuites>'
        '<testsuite name="A" tests="1" failures="1" success="1" errors="0" '
        'time="1"/>'
        '<testsuite name="B" tests="2" failures="2" success="2" errors="0" '
        'time="2"/>'
        '<testsuite/>'
        '</testsuites>', self.tmp.getvalue())

  def test_always_write(self):
    self.log = CtsTestLogger(self.tmp, always_write=True, timer=ZeroTimer())
    self.log.start('A', 1)
    self.assertEqual(
        '<testsuites>'
        '<testsuite name="A" tests="1"/>'
        '</testsuites>', self.tmp.getvalue())

  def test_start_twice_no_time_reset(self):
    self.log.start('A', 1)
    self.log.start('A', 2)
    self.log.done(1, 1)
    self.log.write()
    self.assertEqual(
        '<testsuites>'
        '<testsuite name="A" tests="2" failures="1" success="1" errors="0" '
        'time="1"/>'
        '<testsuite/>'
        '</testsuites>', self.tmp.getvalue())

  def test_not_executed_shows_skipped(self):
    self.log.start('A', 2, ['e', 'f'])
    self.log.done(1, 1)
    self.log.write()
    self.assertEqual(
        '<testsuites>'
        '<testsuite name="A" tests="2" failures="1" success="1" errors="0" '
        'time="3">'
        '<testcase name="e" status="run" result="completed" time="1" '
        'classname="">'
        '<skipped type="unittest.case.SkipTest">'
        '<![CDATA[not yet run]]>'
        '</skipped>'
        '</testcase>'
        '<testcase name="f" status="run" result="completed" time="2" '
        'classname="">'
        '<skipped type="unittest.case.SkipTest">'
        '<![CDATA[not yet run]]>'
        '</skipped>'
        '</testcase>'
        '</testsuite>'
        '<testsuite/>'
        '</testsuites>', self.tmp.getvalue())

  def test_does_not_remove_non_skipped(self):
    self.log.start('A', 2, ['ee', 'f'])
    self.log.success('e')
    self.log.success('ee')
    self.log.done(1, 1)
    self.log.write()
    self.assertEqual(
        '<testsuites>'
        '<testsuite name="A" tests="2" failures="1" success="1" errors="0" '
        'time="5">'
        '<testcase name="f" status="run" result="completed" time="2" '
        'classname="">'
        '<skipped type="unittest.case.SkipTest">'
        '<![CDATA[not yet run]]>'
        '</skipped>'
        '</testcase>'
        '<testcase name="e" status="run" result="completed" time="3" '
        'classname=""/>'
        '<testcase name="ee" status="run" result="completed" time="4" '
        'classname=""/>'
        '</testsuite>'
        '<testsuite/>'
        '</testsuites>', self.tmp.getvalue())

  def test_records_time_if_provided(self):
    self.log.start('A', 1)
    self.log.success('e', 100)
    self.log.done(1, 1)
    self.log.write()
    self.assertEqual(
        '<testsuites>'
        '<testsuite name="A" tests="1" failures="1" success="1" errors="0" '
        'time="2">'
        '<testcase name="e" status="run" result="completed" time="100" '
        'classname=""/>'
        '</testsuite>'
        '<testsuite/>'
        '</testsuites>', self.tmp.getvalue())

  def test_fail_does_not_overwrite_success(self):
    self.log.start('A', 1)
    self.log.success('e', 100)
    self.log.fail('e', 'This should not be visible')
    self.log.done(1, 1)
    self.log.write()
    self.assertEqual(
        '<testsuites>'
        '<testsuite name="A" tests="1" failures="1" success="1" errors="0" '
        'time="2">'
        '<testcase name="e" status="run" result="completed" time="100" '
        'classname=""/>'
        '</testsuite>'
        '<testsuite/>'
        '</testsuites>', self.tmp.getvalue())

  def test_success_overwrites_fail(self):
    self.log.start('A', 1)
    self.log.fail('e', 'Ignored')
    self.log.success('e', 100)
    self.log.done(1, 1)
    self.log.write()
    self.assertEqual(
        '<testsuites>'
        '<testsuite name="A" tests="1" failures="1" success="1" errors="0" '
        'time="3">'
        '<testcase name="e" status="run" result="completed" time="100" '
        'classname=""/>'
        '</testsuite>'
        '<testsuite/>'
        '</testsuites>', self.tmp.getvalue())

  def test_executed_does_not_show_skipped(self):
    self.log.start('A', 2, ['e', 'f'])
    self.log.success('e')
    self.log.done(1, 1)
    self.log.write()
    self.assertEqual(
        '<testsuites>'
        '<testsuite name="A" tests="2" failures="1" success="1" errors="0" '
        'time="4">'
        '<testcase name="f" status="run" result="completed" time="2" '
        'classname="">'
        '<skipped type="unittest.case.SkipTest">'
        '<![CDATA[not yet run]]>'
        '</skipped>'
        '</testcase>'
        '<testcase name="e" status="run" result="completed" time="3" '
        'classname=""/>'
        '</testsuite>'
        '<testsuite/>'
        '</testsuites>', self.tmp.getvalue())


if __name__ == '__main__':
  absltest.main()
