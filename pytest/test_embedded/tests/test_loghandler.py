import logging
from queue import Empty, Queue
from threading import Condition, Thread
from unittest.mock import patch, Mock, MagicMock
import subprocess
import pytest
import time
from functools import partial

from emu.logging.log_handler import LogHandler, QueueLogHandler


@pytest.fixture
def logger():
    return logging.getLogger("test_logger")


@pytest.fixture
def handler(logger):
    return QueueLogHandler(logger)


@pytest.fixture
def log_handler():
    logger = logging.getLogger("test_logger")
    return LogHandler(logger=logger)


@pytest.fixture
def mock_subprocess():
    with patch("subprocess") as mock_subproc:
        yield mock_subproc


@pytest.fixture
def fake_pipe(handler):
    pipe = Queue()
    pipe.put("line 1\n")
    pipe.put("line 2\n")
    pipe.put("line 3\n")
    pipe.put("")

    def readline():
        try:
            return pipe.get(block=False)
        except Empty:
            return ""

    pipe.readline = readline
    return pipe


@pytest.mark.timeout(timeout=2, func_only=True)
def test_with_std_out_logger(logger, handler):
    handler.with_std_out_logger(logger.debug)
    assert handler.std_out_log == logger.debug


@pytest.mark.timeout(timeout=2, func_only=True)
def test_with_std_err_logger(logger, handler):
    handler.with_std_err_logger(logger.debug)
    assert handler.std_err_log == logger.debug


@pytest.mark.timeout(timeout=2, func_only=True)
def test_queue_log__reader(logger, handler, caplog, fake_pipe):
    logfn = logger.info
    handler._reader(fake_pipe, logfn)

    assert caplog.record_tuples == [
        ("test_logger", logging.INFO, "line 1"),
        ("test_logger", logging.INFO, "line 2"),
        ("test_logger", logging.INFO, "line 3"),
    ]


@pytest.mark.timeout(timeout=2, func_only=True)
def test_start_log_proc_logs_stdout_and_stderr(log_handler, caplog):
    mock_proc = Mock(spec=subprocess.Popen)
    mock_proc.stdout = MagicMock()
    mock_proc.stdout.readline.side_effect = ["Hello stdout\n", ""]
    mock_proc.stderr = MagicMock()
    mock_proc.stderr.readline.side_effect = ["Hello, stderr\n", ""]

    log_handler.start_log_proc(mock_proc)
    time.sleep(0.2)
    assert "Hello stdout" in caplog.messages
    assert "Hello, stderr" in caplog.messages


@pytest.mark.timeout(timeout=2, func_only=True)
def test_start_log_proc_logs_stdout_to_handler(handler):
    mock_proc = Mock(spec=subprocess.Popen)
    mock_proc.stdout = MagicMock()
    mock_proc.stdout.readline.side_effect = ["Hello stdout\n", ""]
    mock_proc.stderr = MagicMock()
    mock_proc.stderr.readline.side_effect = ["Hello, stderr\n", ""]

    handler.start_log_proc(mock_proc)
    messages = []
    for line in handler:
        messages.append(line)

    assert "Hello stdout" in messages


@pytest.mark.timeout(timeout=2, func_only=True)
def test_start_log_proc_logs_stdout_to_handler_timeouts(logger):
    stdout_count = 0
    stderr_count = 0

    def stdout_messages(*args, **kwargs):
        nonlocal stdout_count
        stdout_count += 1
        time.sleep(0.2)
        return "Hello stdout\n" if stdout_count == 1 else ""

    def stderr_messages(*args, **kwargs):
        nonlocal stderr_count
        stderr_count += 1
        time.sleep(0.3)
        return "Hello stderr\n" if stderr_count == 1 else ""

    handler = QueueLogHandler(logger, timeout=0.5)
    mock_proc = Mock(spec=subprocess.Popen)
    mock_proc.stdout = MagicMock()
    mock_proc.stdout.readline.side_effect = stdout_messages
    mock_proc.stderr = MagicMock()
    mock_proc.stderr.readline.side_effect = stderr_messages

    handler.start_log_proc(mock_proc)
    lines = []
    for line in handler:
        lines.append(line)

    assert "Hello stdout" in lines
    assert "Hello stderr" in lines


@pytest.mark.timeout(timeout=2, func_only=True)
def test_queue_log_handler_readlines(handler):
    """Test that the QueueLogHandler.readlines() method can read all log messages from the queue."""
    handler.queue.put("This is a log message.")
    assert handler.readlines() == ["This is a log message."]


@pytest.mark.timeout(timeout=2, func_only=True)
def test_queue_log_handler_available(handler):
    """Test that the QueueLogHandler.available() method can return the number of log messages that are currently in the queue."""
    handler.queue.put("This is a log message.")
    assert handler.available() == 1


@pytest.mark.timeout(timeout=2, func_only=True)
def test_log_handler_with_std_out_logger(logger):
    """Test that the LogHandler.with_std_out_logger() method can change the function used for logging the standard output."""
    handler = LogHandler(logger)
    old_log_fn = handler.std_out_log
    handler.with_std_out_logger(lambda x: x.upper())
    assert handler.std_out_log("hello world") == "HELLO WORLD"
    handler.with_std_out_logger(old_log_fn)


@pytest.mark.timeout(timeout=2, func_only=True)
def test_log_handler_with_std_err_logger(logger):
    """Test that the LogHandler.with_std_err_logger() method can change the function used for logging the standard error."""
    handler = LogHandler(logger)
    old_log_fn = handler.std_err_log
    handler.with_std_err_logger(lambda x: x.upper())
    assert handler.std_err_log("hello world") == "HELLO WORLD"
    handler.with_std_err_logger(old_log_fn)


@pytest.mark.timeout(timeout=2, func_only=True)
def test_queue_log_handler_log_to_queue(handler):
    """Test that the QueueLogHandler.log_to_queue() method can log the output of a process to the queue."""
    handler.log_to_queue(logging.info, "This is a log message.")
    assert handler.queue.get() == "This is a log message."


@pytest.mark.timeout(timeout=2, func_only=True)
def test_log_to_queue_calls_log_function_and_continues_on_exception(handler):
    """Test that log_to_queue() calls the log function, and that it continues even if the log function raises an exception."""

    def log(message):
        raise Exception("This is an exception.")

    handler.log_to_queue(log, "This is a log message.")

    # The log function should have been called, even though it raised an exception.
    assert handler.queue.get() == "This is a log message."


@pytest.mark.timeout(timeout=2, func_only=True)
def test_queue_log_handler_finished_2x_has_sentinel(handler):
    """Test that the QueueLogHandler.finished() method can add a "finished" sentinel message to the queue."""
    handler.finished()
    handler.finished()
    assert handler.queue.get() == QueueLogHandler.__FINISHED_SENTINEL__


@pytest.mark.timeout(timeout=2, func_only=True)
def test_queue_log_handler_finished_2x_next_raises_stop(handler):
    """Test that the QueueLogHandler.finished() method can add a "finished" sentinel message to the queue."""
    handler.finished()
    handler.finished()
    with pytest.raises(StopIteration):
        next(handler)


@pytest.mark.timeout(timeout=2, func_only=True)
def test_queue_log_handler_iter(logger):
    """Test that the QueueLogHandler.__iter__() method can iterate over the log messages in the queue."""
    handler = QueueLogHandler(logger, timeout=0.2)
    handler.queue.put("This is a log message.")
    handler.queue.put("This is another log message.")
    assert list(handler) == ["This is a log message.", "This is another log message."]


@pytest.mark.timeout(timeout=2, func_only=True)
def test_queue_log_handler_readlines_empty_queue(handler):
    """Test that the QueueLogHandler.readlines() method returns an empty list when the queue is empty."""
    assert handler.readlines() == []


@pytest.mark.timeout(timeout=2, func_only=True)
def test_queue_log_handler_available_empty_queue(handler):
    """Test that the QueueLogHandler.available() method returns 0 when the queue is empty."""
    assert handler.available() == 0


@pytest.mark.timeout(timeout=2, func_only=True)
def test_queue_log_handler_finished_2x_unblocks_queue_with_sentinel(handler):
    """Test that when the QueueLogHandler.finished() method is called, the queue will be unblocked."""
    with pytest.raises(Empty):
        handler.queue.get(timeout=0.1)

    handler.finished()
    handler.finished()
    # The thread should now be unblocked and able to get the log message from the queue.
    assert handler.queue.get() == QueueLogHandler.__FINISHED_SENTINEL__


@pytest.mark.timeout(timeout=2, func_only=True)
def test_queue_log_handler_iterator_timeout_and_finish(logger):
    """Test that an iterator will timeout and finish."""
    handler = QueueLogHandler(logger, timeout=0.1)

    for line in handler:
        pass

    # The iterator should now be finished and there should be no more log messages in the queue.
    assert handler.queue.empty()


@pytest.mark.timeout(timeout=2, func_only=True)
def test_queue_log_handler_iterator_blocks_and_waits_for_item(logger):
    """Test that the iterator blocks and waits until another thread places an item in the QueueLogHandler."""
    handler = QueueLogHandler(logger, timeout=0.5)

    # Create a thread that will place an item in the queue.
    def put_item():
        handler.queue.put("This is a log message.")

    thread = Thread(target=put_item)
    thread.start()

    # Block the thread until the iterator gets an item from the queue.
    for line in handler:
        pass

    # The iterator should now be unblocked and have the log message from the queue.
    assert line == "This is a log message."

    # The thread that placed the item in the queue should be finished.
    assert thread.is_alive() is False


@pytest.mark.timeout(timeout=2, func_only=True)
def test_queue_log_handler_iterator_blocks_and_waits_for_item_with_condition_variable(
    handler,
):
    """Test that the iterator blocks and waits until another thread places an item in the QueueLogHandler using a condition variable."""

    # Create a condition variable to signal when an item is available in the queue.
    condition = Condition()
    has_item = False

    # Create a thread that will place an item in the queue and signal the condition variable.
    def put_item():
        with condition:
            nonlocal has_item
            handler.queue.put("This is a log message.")
            has_item = True
            condition.notify()
            handler.finished()

    thread = Thread(target=put_item)
    thread.start()

    # Block the thread until the iterator gets an item from the queue.
    with condition:
        while not has_item:
            condition.wait()

    # The iterator should now be unblocked and have the log message from the queue.
    assert next(handler) == "This is a log message."

    # The thread that placed the item in the queue should be finished.
    assert thread.is_alive() is False
