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
from threading import Thread
from functools import partial
import six

if six.PY2:
    from Queue import Queue
else:
    from queue import Queue


def run(cmd, local_env=None):
    """Runs the command, logging the out put to the logger."""
    use_shell = platform.system() == "Windows"
    if not local_env:
        local_env = os.environ

    # Make sure the local_env only contains strings.
    for key in local_env:
        local_env[key] = str(local_env[key])

    logging.info("Launching %s with: %s", cmd, local_env)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=use_shell,
        env=local_env,
    )

    q = _log_proc(proc)
    return proc, q


def log_to_queue(q, line):
    """Logs the output of the given process."""
    if q.full():
        q.get()

    logging.info(line)
    q.put(line)


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
        Thread(target=_reader, args=args).start()

    return q