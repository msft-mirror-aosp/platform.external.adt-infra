# Copyright 2020 - The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import os
import platform
import subprocess
from functools import partial
from queue import Queue
from threading import Thread

import sh


def run(
    cmd: list[str], local_env: dict[str, str] = {}
) -> tuple[subprocess.Popen, Queue]:
    """Runs the given command, directing stderr & stdout to the python logger.

    Args:
        cmd (list[str]): Command to execute
        local_env (dict[str, str], optional): Environment to merge into default environment. Defaults to {}.

    Returns:
        _type_: _description_
    """
    use_shell = platform.system() == "Windows"
    env = os.environ

    # Make sure the local_env only contains strings.
    for key in local_env:
        env[key] = str(local_env[key])

    logging.info("Launching %s with: %s", cmd, env)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=use_shell,
        env=env,
    )

    q = _log_proc(proc)
    return proc, q


def log_to_queue(q, line):
    """Logs the output of the given process."""
    if q.full():
        q.get()

    strip = line.strip()
    logging.info(strip)
    q.put(strip)


def _reader(pipe, logfn):
    try:
        with pipe:
            for line in iter(pipe.readline, b""):
                logfn(line[:-1].decode("utf-8").strip())
    finally:
        pass


def _log_proc(proc):
    """Logs the output of the given process."""
    q = Queue()
    log_with_queue = partial(log_to_queue, q)
    for args in [[proc.stdout, log_with_queue], [proc.stderr, logging.error]]:
        t = Thread(target=_reader, args=args)
        t.start()

    return q


class LogObserver(object):
    def __init__(self, logfile):
        """Attaches a log queue to a file."""
        self.queue = Queue()
        log_with_queue = partial(log_to_queue, self.queue)
        self.tail = sh.tail("-f", logfile, _out=log_with_queue, _bg=True)

    def __del__(self):
        self.tail.kill()
