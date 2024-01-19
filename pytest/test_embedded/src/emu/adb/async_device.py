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
import os
import re
import time
from shlex import quote as cmd_quote

import aiofiles
from ppadb import InstallError
from ppadb.client_async import ClientAsync
from ppadb.connection_async import ConnectionAsync
from ppadb.device_async import DeviceAsync
from ppadb.protocol import Protocol
from ppadb.sync.stats import S_IFREG
from ppadb.sync_async import SyncAsync

from emu.logging.log_handler import AsyncLogHandler


class AdbDeviceNotFound(Exception):
    pass


class DeviceStream:
    """A wrapper around the I/O adb stream between the emulator and this process"""

    def __init__(self, conn: ConnectionAsync, logger=logging):
        self.conn = conn
        self.handler = AsyncLogHandler(logger)
        self.task = None

    async def __aenter__(self):
        reader: asyncio.StreamReader = self.conn.reader
        # We do not want to await the completion of the logger,
        # It should complete when the DeviceStream gets cleaned out.
        self.task = asyncio.create_task(self.handler.async_log_stream(reader))
        return self.handler

    async def __aexit__(self, type, value, traceback):
        await self.conn.close()
        if not self.task.done():
            self.task.cancel()


def _get_src_info(src):
    """Gets information about the given file."""
    exists = os.path.exists(src)
    isfile = os.path.isfile(src)
    isdir = os.path.isdir(src)
    basename = os.path.basename(src)
    walk = None if not isdir else list(os.walk(src))

    # Note this is broken in ppad.DeviceAsync
    timestamp = int(os.stat(src).st_mtime)
    total_size = os.path.getsize(src)

    return exists, isfile, isdir, basename, walk, timestamp, total_size


class AdbDeviceAsync:
    """This class is using the compose pattern to fix a series of bugs that we cannot fix in ppad.DeviceAsync"""

    def __init__(self, device: DeviceAsync, host: ClientAsync, logger=logging):
        self.device = device
        self.host = host
        self.logger = logger

    async def _push(self, src, dest, mode, progress):
        DATA_MAX_LENGTH = 65536
        (
            exists,
            isfile,
            isdir,
            basename,
            walk,
            timestamp,
            total_size,
        ) = await asyncio.get_running_loop().run_in_executor(None, _get_src_info, src)

        # Create a new connection for file transfer
        sync_conn = await self.device.sync()
        helper = SyncAsync(sync_conn)
        async with sync_conn:
            sent_size = 0

            # SEND
            mode = mode | S_IFREG
            args = f"{dest},{mode}"
            await helper._send_str(Protocol.SEND, args)

            # DATA
            async with aiofiles.open(src, "rb") as stream:
                while True:
                    chunk = await stream.read(DATA_MAX_LENGTH)
                    if not chunk:
                        break

                    sent_size += len(chunk)
                    await helper._send_length(Protocol.DATA, len(chunk))
                    await sync_conn.write(chunk)

                    if progress is not None:
                        progress(src, total_size, sent_size)

            # DONE
            await helper._send_length(Protocol.DONE, timestamp)
            await sync_conn._check_status()

    async def push(self, src, dest, mode=0o644, progress=None):
        (
            exists,
            isfile,
            isdir,
            basename,
            walk,
            _,
            _,
        ) = await asyncio.get_running_loop().run_in_executor(None, _get_src_info, src)
        if not exists:
            raise FileNotFoundError(f"Cannot find {src}")

        if isfile:
            await self._push(src, dest, mode, progress)

        elif isdir:
            for root, dirs, files in walk:
                root_dir_path = os.path.join(basename, root.replace(src, ""))

                await self.shell(f"mkdir -p {dest}/{root_dir_path}")

                for item in files:
                    await self._push(
                        os.path.join(root, item),
                        os.path.join(dest, root_dir_path, item),
                        mode,
                        progress,
                    )

    async def pull(self, src, dest):
        return await self.device.pull(src, dest)

    async def shell(self, cmd, timeout=None) -> str:
        timestr = f" ({timeout}s)" if timeout else ""
        self.logger.info("shell%s: %s", timestr, cmd)
        device_stream = await self.shell_stream(cmd, timeout)
        async with device_stream as stream:
            res = await asyncio.wait_for(stream.read_all(), timeout=timeout)
            self.logger.info("shell (result): %s", res)
            return res

    async def shell_stream(self, cmd, timeout=None) -> DeviceStream:
        conn: ConnectionAsync = await self.device.create_connection(timeout=timeout)
        timestr = f" ({timeout}s)" if timeout else ""
        self.logger.info("shell_stream%s: %s", timestr, cmd)

        cmd = "shell:{}".format(cmd)
        await conn.send(cmd)

        return DeviceStream(conn, self.logger)

    async def is_installed(self, package):
        result = await self.shell("pm path {}".format(package))
        return "package:" in result

    async def get_state(self):
        cmd = f"host-serial:{self.device.serial}:get-state"
        return await self.host._execute_cmd(cmd)

    async def install(
        self,
        path,
        forward_lock=False,  # -l
        reinstall=False,  # -r
        test=False,  # -t
        installer_package_name="",  # -i {installer_package_name}
        shared_mass_storage=False,  # -s
        internal_system_memory=False,  # -f
        downgrade=False,  # -d
        grant_all_permissions=False,  # -g
    ):
        dest = f"/data/local/tmp/{os.path.basename(path)}"
        await self.push(path, dest)

        parameters = []
        if forward_lock:
            parameters.append("-l")
        if reinstall:
            parameters.append("-r")
        if test:
            parameters.append("-t")
        if len(installer_package_name) > 0:
            parameters.append(f"-i {installer_package_name}")
        if shared_mass_storage:
            parameters.append("-s")
        if internal_system_memory:
            parameters.append("-f")
        if downgrade:
            parameters.append("-d")
        if grant_all_permissions:
            parameters.append("-g")

        try:
            result = await self.shell(
                "pm install {} {}".format(" ".join(parameters), cmd_quote(dest))
            )
            match = re.search(self.device.INSTALL_RESULT_PATTERN, result)

            if match and match.group(1) == "Success":
                return True
            elif match:
                groups = match.groups()
                raise InstallError(dest, groups[1])
            else:
                raise InstallError(dest, result)
        finally:
            await self.shell(f"rm -f {dest}")

    async def wait_boot_complete(self, timeout=60, timedelta=1):
        """
        Asynchronously waits for boot completion (up to a timeout) by polling a shell command.

        :param timeout: Maximum time to wait in seconds (default: 60).
        :param timedelta: Interval between polling attempts in seconds (default: 1).
        """

        cmd = "getprop sys.boot_completed"
        end_time = time.time() + timeout

        while True:
            try:
                # Execute shell command asynchronously
                result = await self.shell(cmd)

                if result.strip() == "1":
                    return True

            except RuntimeError as e:
                logging.error(e)

            # Check for timeout
            if time.time() > end_time:
                raise TimeoutError()

            # Wait before next check (asynchronously)
            if timedelta > 0:
                await asyncio.sleep(timedelta)
