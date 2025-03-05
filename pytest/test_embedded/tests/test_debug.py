# Copyright 2024 The Android Open Source Project
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
import re
import logging
import asyncio
import shutil
import pytest
import platform
from emu.timing import eventually
from emu.process.command import Command


@pytest.fixture
async def jdb(avd):
    """A fixture that gives access to the Java Debugger (JDB)

    Once the fixture is requested, you usually want to use it like this:

        avd.start_activity(activity, params="-D") # Launch app with debug enabled
        jdb.attach(package) # Attach jdb to the package
        jdb.send(command, msg) # Send a jdb command and (optionally) check if
                               # 'msg' appears in the jdb output

    Args:
        avd (BaseEmulator): Fixture that gives access to the configured emulator.

    Yields:
        Jdb: An instance of the Jdb class
    """

    class Jdb:
        """Provides methods to debug an app using Java Debugger (jdb)"""

        def __init__(self):
            self.jdb_bin = "jdb"
            self.app_pid = None
            self.cmd = None
            if platform.system() == "Windows":
                self.jdb_bin += ".exe"
            self.jdb_path = shutil.which(self.jdb_bin)
            if not self.jdb_path:
                pytest.fail(f"jdb binary not found in PATH.")

        async def attach(self, pkg):
            """Attach JDB to a given package

            Args:
                pkg (str): Package name

            Returns:
                Jdb: jdb instance

            Notes:
                This method will perform the following tasks:
                1. Check if the app to be debugged hosts a JDWP transport interface.
                2. Forward the JDWP socket to a randomly assigned TCP port.
                3. Attach JDB to the process' PID.
                4. Verify that JDB is ready to receive commands.
            """
            assert await self._get_pid(pkg), f"Couldn't find {pkg} pid."

            # Check if the app hosts a JDWP transport interface.
            exit_code, pids = await avd.adb.run(["jdwp"])
            assert self.app_pid in pids, f"{pkg} pid doesn't host a JDWP transport."

            # Forward JDWP socket to a random tcp port.
            await avd.adb.run(f"forward tcp:0 jdwp:{self.app_pid}".split())
            _, output = await avd.adb.run("forward --list".split())
            assert (
                f"jdwp:{self.app_pid}" in output[0]
            ), "Couldn't forward JDWP socket connection."

            # Grab the assigned TCP port.
            tcp_port, _ = re.findall("tcp:(.*) jdwp:(.*)", output[0])[0]
            logging.info(f"Forwarded JDWP socket through tcp port {tcp_port}.")

            # Attach jdb to process.
            params = ["-attach", f"localhost:{tcp_port}"]
            self.cmd = Command([self.jdb_path] + params)
            try:
                await asyncio.wait_for(self.cmd.run(use_stdin_pipe=True), timeout=30)
            except (Exception, asyncio.TimeoutError) as err:
                logging.error("Timed out while attempting to attach jdb: %s", err)
                raise

            # Verify jdb is initialized.
            assert await (
                self.string_in_output("Initializing jdb")
            ), "Couldn't initialize jdb."

            logging.info("Jdb initialized successfully.")
            return self

        async def _get_pid(self, pkg):
            # Return True if the PID of package 'pkg' is found
            async def _do_get_pid():
                self.app_pid = await avd.adb.exec_out(f"pidof {pkg}")
                if len(self.app_pid) > 0:
                    return True

            return await eventually(_do_get_pid)

        async def send(self, cmd, message=None, timeout=30):
            """Send a jdb command.

               Optionally, return True if 'message' appears in the log.

            Args:
                cmd (str): jdb command to send
                message (str): output message to check against.
                               If message is None, the output is not read.
                timeout (int, optional): timeout for reading output. Defaults to 30.

            Returns:
                bool: True if 'message' appears in the jdb output log
            """
            # Send jdb command
            logging.info(f"jdb: sending command '{cmd}'")
            encoded_cmd = (cmd + "\n").encode("UTF-8")
            self.cmd.process.stdin.write(encoded_cmd)
            await self.cmd.process.stdin.drain()
            if message is None:
                return
            # Check if 'message' appears in jdb output
            return await self.string_in_output(message)

        async def read(self) -> [str]:
            """Read JDB output"""
            return self.cmd.handler.readlines()

        async def string_in_output(self, string, timeout=30):
            """Return 'True' if 'string' is observed in the jdb output."""

            async def _string_in_output():
                async for line in self.cmd.handler:
                    if string in line:
                        logging.info(f"Matched line '{line}'")
                        return True

            return await eventually(_string_in_output, timeout=timeout)

    jdb = Jdb()
    yield jdb
    logging.info("<-- teardown jdb")
    if jdb.cmd:
        await jdb.cmd.cancel()
    logging.info("=== finalized jdb")


async def screenshots_equal(screenshot1, screenshot2):
    """Return True if two screenshots are identical pixel-by-pixel."""
    return (
        list(screenshot1.getdata()) == list(screenshot2.getdata())
        and screenshot1.size == screenshot2.size
    )


@pytest.mark.sanity
@pytest.mark.async_timeout(500)
async def test_can_debug(avd, jdb, get_screenshot, install_animation_apk):
    """Verify test app can be debugged on the emulator.

    Args:
        avd (BaseEmulator): Fixture that gives access to the running emulator.
        jdb (Jdb): Fixture that gives access to the Java Debugger
        get_screenshot (callback): screenshot service fixture.

    Test Steps:
        1. Launch test app with the debug flag enabled.
        2. Attach jdb to the package pid.
        3. Set a breakpoint (Verify 1 and 2).
        4. Clear the breakpoint and resume the execution (Verify 3).

    Verification:
        1. The message "Breakpoint hit" should appear in jdb log.
        2. The app's execution should be paused.
        3. The app's execution should be resumed.
    """

    async def screen_is_paused(n=4, delay=0.5):
        # Return 'True' if 'n' consecutive screenshots are identical.
        _, screenshot_ = await get_screenshot()
        for i in range(n - 1):
            await asyncio.sleep(delay)
            _, screenshot = await get_screenshot()
            logging.info(f"Comparing screenshots [{i+1}/{n-1}] ...")
            comp = await screenshots_equal(screenshot_, screenshot)
            if comp == False:
                return False
        return True

    await install_animation_apk.start(params="-D")
    assert await eventually(install_animation_apk.is_running), \
        "Couldnt' launch AnimateBox in Debug mode."
    await asyncio.sleep(10)

    # Attach jdb to the package.
    await jdb.attach(install_animation_apk.package_name)

    # Allow the Animation to run for a few seconds.
    await asyncio.sleep(10)

    # Set a breakpoint and verify it is hit.
    logging.info("Attempting to set breakpoint ..")
    assert await jdb.send(
        "stop in com.google.emu.Triangle.draw",
        "Breakpoint hit: ",
    ), "Couldn't verify the breakpoing was hit."
    await asyncio.sleep(10)

    # Verify if the screen is paused.
    assert await screen_is_paused(), "The Animatebox box is not stopped."

    # Clear the breakpoint and verify it is removed.
    logging.info("Attempting to clear the breakpoint ..")
    assert await jdb.send(
        "clear com.google.emu.Triangle.draw",
        "Removed: breakpoint com.google.emu.Triangle.draw",
    ), "Couldn't verify the breakpoing was removed."
    logging.info("jdb: removed breakpoint 'com.google.emu.Triangle.draw'.")

    # Resume debug.
    logging.info("jdb: attempting to resume debug")
    await jdb.send("cont")

    # Verify if the screen presents visual changes.
    assert not await screen_is_paused(), "The Animatebox app didn't resume."
