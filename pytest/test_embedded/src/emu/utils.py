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


def system_cpu() -> str:
    """Returns the native system cpu

    Returns:
        str: The native system cpu, either x86_64|arm64
    """
    aarch = platform.machine()
    if aarch == "x86_64":
        # Ok maybe python is running under rosetta, if so the uname.version
        # will have have something along RELEASE_ARM64_T6000 in it
        uname = platform.uname()
        if "ARM64" in uname.version and uname.system == "Darwin":
            return "arm64"

    return aarch


def run(
    cmd: list[str], local_env: dict[str, str] = {}
) -> tuple[subprocess.Popen, Queue]:
    """Runs the given command, directing stderr & stdout to the python logger.

    Args:
        cmd (list[str]): Command to execute
        local_env (dict[str, str], optional): Environment to merge into default environment. Defaults to {}.

    Returns:
        tuple[subprocess.Popen, Queue]: Handle to the process, queue with system output
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


def log_to_queue(logging_queue, line):
    """Logs the output of the given process."""
    if logging_queue.full():
        logging_queue.get()

    strip = line.strip()
    logging.info(strip)
    logging_queue.put(strip)


def _reader(pipe, logfn):
    try:
        with pipe:
            for line in iter(pipe.readline, b""):
                logfn(line[:-1].decode("utf-8").strip())
    finally:
        pass


def _log_proc(proc):
    """Logs the output of the given process."""
    log_queue = Queue()
    log_with_queue = partial(log_to_queue, log_queue)
    for args in [[proc.stdout, log_with_queue], [proc.stderr, logging.error]]:
        thread = Thread(target=_reader, args=args)
        thread.start()

    return log_queue


class LogObserver(object):
    def __init__(self, logfile):
        """Attaches a log queue to a file."""
        self.queue = Queue()
        log_with_queue = partial(log_to_queue, self.queue)
        self.tail = sh.tail("-f", logfile, _out=log_with_queue, _bg=True)

    def __del__(self):
        self.tail.kill()
