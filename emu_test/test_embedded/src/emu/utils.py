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

    Thread(target=_log_std_out, args=[proc]).start()
    return proc


def _reader(pipe, queue):
    try:
        with pipe:
            for line in iter(pipe.readline, b""):
                queue.put((pipe, line[:-1]))
    finally:
        queue.put(None)


def _log_std_out(proc):
    """Logs the output of the given process."""
    q = Queue()
    Thread(target=_reader, args=[proc.stdout, q]).start()
    Thread(target=_reader, args=[proc.stderr, q]).start()
    for _ in range(2):
        for _, line in iter(q.get, None):
            logging.info(line)
