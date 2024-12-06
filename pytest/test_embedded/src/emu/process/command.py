# Copyright 2024 - The Android Open Source Project
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
import asyncio
import logging
import os
from pathlib import Path

import psutil

from emu.logging.log_handler import AsyncLogHandler
from emu.process.kill_emulator import kill_process_tree


class Command:
    """
    Represents an asynchronous command to be executed in a subprocess.

    Provides methods to manage environment variables, working directory, and execute the command with logging.
    """

    def __init__(self, cmd, logger=None):
        """
        Initializes the Command instance.

        Args:
            cmd (list[str]): The command to be executed, as a list of strings (e.g., ["ls", "-l"]).
            logger (logging.Logger, optional): A logger instance for logging output. If not provided,
                                               a logger named after the command is created.
        """

        self.env = os.environ.copy()  # Make a copy of the environment
        self.cmd = [str(c) for c in cmd]
        self.process = None

        if not logger:
            name = Path(cmd[0]).name
            self.handler = AsyncLogHandler(logging.getLogger(f"{name}"))
        else:
            self.handler = AsyncLogHandler(logger)  # Use provided logger
        self.working_directory = None
        self.log_task = None

    def with_environment(self, env: dict[str, str]):
        """
        Adds or updates environment variables for the command execution.

        Args:
            env (dict[str, str]): A dictionary of environment variables (key=name, value=value).

        Returns:
            self: The Command instance for method chaining.
        """

        self.env.update(env)  # Update the environment dictionary
        return self

    def in_directory(self, directory):
        """
        Sets the working directory for the command execution.

        Args:
            directory (str or Path): The path to the working directory.

        Returns:
            self: The Command instance for method chaining.
        """

        self.working_directory = Path(directory)
        return self

    async def __aenter__(self):
        return self.handler

    async def __aexit__(self, type, value, traceback):
        if self.log_task and not self.log_task.done():
            self.log_task.cancel()

    async def cancel(self):
        """Cancel and terminate the outstanding process.

        The process, and all its descendants will be forcefully terminated.
        """
        if self.log_task and not self.log_task.done():
            self.log_task.cancel()
        if self.process:
            try:
                proc = psutil.Process(self.process.pid)
                if proc.is_running():
                    logging.info("Forcefully terrminating: %s", proc)
                    kill_process_tree(proc)
            except psutil.NoSuchProcess:
                # Proc is dead
                pass

    async def wait(self):
        """Wait until the process exit and return the process return code."""
        proc = await self.process.wait()

        # The logtask should be closed out soon, we want to make sure all the logs
        # have been handled before returning.
        await asyncio.wait_for(self.log_task, timeout=1)
        return proc

    def is_running(self):
        """Checks if the command's process is still running.

        Returns:
            bool: True if the process is running, False otherwise.
        """
        if self.process:  # Check if the process has been started
            return self.process.returncode is None  # None means still running
        return False

    async def run(self, use_stdin_pipe=False):
        """
        Creates a subprocess to execute the command.

        A logger will be attached that will log the output from stdout/stderr
        a log handler that will log it logger.info/logger.warning.

        Arguments:
            used_stdin_pipe (bool): True to pipe stdin. Defaults to False.

        Returns:
            asyncio.subprocess.Process: The created subprocess object.
        """

        self.process = await asyncio.create_subprocess_exec(
            *self.cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if use_stdin_pipe else None,
            cwd=self.working_directory,  # Use the working directory if set
            env=self.env,  # Use the specified environment
        )
        cmdstr = " ".join(self.cmd)
        logging.info("Run: %s, (%d)", cmdstr, self.process.pid)
        self.log_task = asyncio.create_task(
            self.handler.async_log(self.process)
        )  # Start logging task
        return self

    async def run_until_finished(self, timeout: int = 10) -> (int, [str]):
        """
        Runs the command, waits for completion (with a timeout), and captures output.

        Args:
            timeout (int, optional): Maximum time (in seconds) to wait for command
            completion. Defaults to 10.

        Returns:
            tuple:
                - exit_code (int): The exit code of the process, -1 in case of timeout and termination.
                - output (list[str]): A list of lines captured from the command's
                  output (stdout and stderr).
        """
        try:
            await asyncio.wait_for(self.run(), timeout=timeout)
            status = await asyncio.wait_for(self.wait(), timeout=timeout)
            res = self.handler.readlines()
            logging.info("Completed: %d", status)
            return status, res
        except (Exception, asyncio.TimeoutError) as err:
            logging.info("Timed out/Error: %s", err)
            try:
                proc = psutil.Process(self.process.pid)
                kill_process_tree(proc)
            except psutil.NoSuchProcess:
                pass
            pid = self.process.pid if self.process else "(no process pid available)"
            logging.info("Terminated pid:%s, returing -1, and lines", pid)
            return -1, self.handler.readlines()
