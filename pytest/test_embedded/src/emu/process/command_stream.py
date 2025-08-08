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
import subprocess


class AsyncCommandStream:
    """
    A utility class to run a command asyncronously and return the output as a stream

    You usually want to use it like this:

    async with AsyncCommandStream(["ping", "www.google.com"]) as stream:
        async for line in stream:
            print(line)
    """

    def __init__(self, command):
        self._command = [str(c) for c in command]
        self._process = None

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._process.returncode is not None:
            raise StopAsyncIteration()
        line = await self._process.stdout.readline()
        return line.decode("utf-8").rstrip()

    async def __aenter__(self):
        # Start the command asynchronously
        self._process = await asyncio.create_subprocess_exec(
            *self._command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._process:
            self._process.terminate()
            await self._process.wait()
