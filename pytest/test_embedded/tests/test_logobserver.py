import queue
import time
from pathlib import Path
from typing import List

import pytest

from emu.utils import LogObserver

pytestmark = pytest.mark.std


def data_writer(log_file: Path, text: List[str]):
    for line in text:
        log_file.write_text(line + "\n")
        time.sleep(0.1)


def test_reads_all_lines_immediately(tmp_path):
    log_file = tmp_path / "hello.txt"
    log_file.write_text("Hello\nWorld\n")
    with LogObserver(log_file) as observer:
        assert "Hello" == observer.get(block=True, timeout=0.5)
        assert "World" == observer.get(block=True, timeout=0.5)


def test_no_lines_times_out(tmp_path):
    log_file = tmp_path / "hello.txt"
    log_file.write_text("")
    with pytest.raises(queue.Empty):
        with LogObserver(log_file) as observer:
            observer.get(block=True, timeout=0.5)


def test_reads_lines_as_they_come(tmp_path):
    log_file = tmp_path / "hello.txt"
    with open(log_file, "w", encoding="utf-8") as test_file:
        with LogObserver(log_file) as observer:
            for msg in ["Hello", "World"]:
                test_file.write(msg + "\n")
                test_file.flush()
                assert msg == str(observer.get(block=True, timeout=0.5))
