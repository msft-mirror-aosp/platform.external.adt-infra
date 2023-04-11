# Copyright 2022 - The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the',  help='License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an',  help='AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import os
import platform
import subprocess
from pathlib import Path

from emu.logging.log_handler import LogHandler, QueueLogHandler
from emu.timing import TimeoutTrigger
from emu.process.kill_emulator import kill_process_tree
import psutil


class Command:
    """A Command that can be run in a shell."""

    def __init__(self, cmd):
        self.env = os.environ
        self.cmd = [str(c) for c in cmd]
        self.log_handler = LogHandler()
        self.working_directory = None
        self.use_shell = platform.system() == "Windows"
        self.ignore_errors = False

    def with_environment(self, env: dict[str, str]):
        """Additional environment to use when running this command

        Args:
            env (dict[str, str]): Environment used to override
                                default os environment.

        Returns:
            Command: The command itself
        """
        for k, v in env.items():
            self.env[str(k)] = str(v)
        return self

    def with_log_handler(self, handler: LogHandler):
        """Sets the log

        Args:
            handler (LogHandler): The loghandler responsible for logging

        Returns:
            Command: The command itself
        """
        self.log_handler = handler
        return self

    def in_directory(self, directory):
        self.working_directory = Path(directory)
        return self

    def run(self):
        """Runs the given command."""
        cmdstr = " ".join(self.cmd)
        logging.info("Run: %s", cmdstr)

        proc: subprocess.Popen = subprocess.Popen(
            self.cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.working_directory,
            shell=self.use_shell,
            env=self.env,
            encoding="utf-8",
        )

        self.log_handler.start_log_proc(proc)
        return proc

    def run_until_finished(self, timeout: int = 10):
        """Runs the command until it is finished, returning the exit code."""

        # Create an infinte queue, so we capture all the output.
        q = QueueLogHandler(logging.getLogger(f"{self.cmd[0]}"), max_lines_to_log=0)
        self.with_log_handler(q)
        proc = self.run()
        with TimeoutKillProcessTrigger(proc.pid, timeout=timeout):
            status = proc.wait(timeout=timeout)

        return status, q.readlines()


class TimeoutKillProcessTrigger(TimeoutTrigger):
    def __init__(self, pid, timeout: int = 60):
        super().__init__(self._handler, timeout)
        self.proc = psutil.Process(pid)

    def _handler(self):
        if self.proc.is_running():
            logging.debug("Killing %s", self.proc)
            kill_process_tree(self.proc)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exits the context and terminates the process."""
        self._handler()
        self.cancel()
