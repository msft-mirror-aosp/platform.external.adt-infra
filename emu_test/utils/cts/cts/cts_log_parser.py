import re
from test_logger import CtsTestLogger

class CtsLogParser(object):

  START_REGEX = R'.* I\/.*: \[.*\] Starting .* (.*) with (\d+) tests'
  SUCCESS_REGEX = R'.* I\/.*: \[.*] (.*) pass$'
  FAIL_REGEX = R'.* I\/.*: \[.*] (.*) fail:(.*)'
  START_OF_LOGLINE = '^\d+-\d+ \d+:\d+:\d+.*'
  DONE_REGEX = R'.* I\/.*: \[.*\] .*\. (\d+) passed, (\d+) failed, (\d+) not executed'

  def __init__(self, fnobject):
    self.cts_logger = CtsTestLogger(fnobject)
    self.fail_buffer = []

  def _is_start(self, line):
    return re.search(CtsLogParser.START_REGEX, line.decode())

  def _add_start(self, line):
    m = re.match(CtsLogParser.START_REGEX, line.decode())
    self.cts_logger.start(m.group(1), int(m.group(2)))

  def _is_done(self, line):
    return re.search(CtsLogParser.DONE_REGEX, line.decode())

  def _add_done(self, line):
    m = re.match(CtsLogParser.DONE_REGEX, line.decode())
    self.cts_logger.done(int(m.group(1)), int(m.group(2)))

  def _is_success(self, line):
    return re.search(CtsLogParser.SUCCESS_REGEX, line.decode())

  def _add_success(self, line):
    self.cts_logger.success(re.match(CtsLogParser.SUCCESS_REGEX, line.decode()).group(1))

  def _is_fail(self, line):
    return re.search(CtsLogParser.FAIL_REGEX, line.decode())

  def _is_logline(self, line):
    return re.search(CtsLogParser.START_OF_LOGLINE, line.decode())

  def _add_fail(self, lines):
    m = re.match(CtsLogParser.FAIL_REGEX, lines[0].decode())
    self.cts_logger.fail(m.group(1), '\n'.join([m.group(2)] + lines[1:]))

  def add(self, line):
    # If this is a new CTS log line then flush the buffer .
    if self._is_logline(line) and self.fail_buffer:
        self._add_fail(self.fail_buffer)
        self.fail_buffer = []

    if self._is_success(line):
        self._add_success(line)
    elif self._is_start(line):
        self._add_start(line)
    elif self._is_done(line):
        self._add_done(line)
    elif self._is_fail(line):
        self.fail_buffer = [line]
    elif self.fail_buffer:
        self.fail_buffer.append(line)

  def flush(self):
    if self.fail_buffer:
      self._add_fail(self.fail_buffer)
    self.cts_logger.write()


