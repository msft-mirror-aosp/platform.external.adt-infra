# Copyright 2024 - The Android Open Source Project
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
import asyncio
import logging
from typing import Optional


class EmulatorClientEOF(Exception):
    pass


class EmulatorClientBadCommand(Exception):
    pass


class EmulatorClient:
    AUTH = "Android Console: Authentication required"

    def __init__(self, port, logger: logging.Logger):
        self.port = port
        self.logger = logger
        self._reader = None
        self._writer = None

    async def login(self):
        self._reader, self._writer = await asyncio.open_connection(
            "localhost", self.port
        )
        lines = await self.read_until_ok_ko()
        if EmulatorClient.AUTH in lines:
            # Last line contains the path to the auth, file.
            await self._auth(lines[-2])

    async def _auth(self, fname: str):
        """Authenticates to the Android emulator using the given auth file.

        Args:
            fname: The path to the auth file in quotes ('path')
        """
        self.logger.info("Authenticating using %s", fname)
        with open(fname[1:-1], "r", encoding="utf-8") as authfile:
            token = authfile.read()
            msg = f"auth {token}".strip()
            await self.send(msg)

    async def send(self, command) -> (bool, [str]):
        self.logger.info("--> %s", command)
        self._writer.write(f"{command}\n".encode())
        return await self.read_until_ok_ko()

    async def read_until_ok_ko(self) -> (bool, [str]):
        lines = []
        async for line in self._reader:  # Async iteration over lines
            line = line.decode().strip()
            self.logger.info("<-- %s", line)
            lines.append(line)
            if line == "OK":
                return lines
            if line == "KO":
                msg = "\n".join(lines)
                raise EmulatorClientBadCommand(f"Invalid command {msg}")

        msg = "\n".join(lines)
        raise EmulatorClientEOF(
            f"EOF before receiving complete emulator response: {msg}"
        )

    @staticmethod
    async def connect(
        port: int,
        emulator_name: Optional[str] = None,
    ):
        """Connects to the Android emulator on the given port and returns an
           EmulatorClient instance.

        Args:
            port: The port that the Android emulator is listening on.
            emulator_name: The name of the emulator. If not specified, the emulator
            name will be `port-{port}`.

        Returns:
            An EmulatorConnection instance.

        Raises:
            IOError: If the connection to the Android emulator cannot be established.
        """
        if not emulator_name:
            emulator_name = f"port-{port}"
        client = EmulatorClient(port, logging.getLogger(f"{emulator_name}-con"))
        await client.login()
        return client
