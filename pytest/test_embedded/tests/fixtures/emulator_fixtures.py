# -*- coding: utf-8 -*-
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
"""Fixtures for launching and controlling the emulator."""
import asyncio
import json
import logging
from pathlib import Path

import pytest

from emu.apk import APP_DEBUG_APK, APP_MOBLY_APK
from emu.emulator import BaseEmulator, DebugEmulator, Emulator
from emu.emulator_exceptions import EmulatorFailedToBootException
from emu.process.command import Command
from emu.utils import system_cpu


@pytest.fixture(scope="module")
@pytest.mark.async_timeout(200)
async def emulator(request, pytestconfig) -> BaseEmulator:
    """Makes a configured emulator available

    Note: You usually don't need fixture, as it will be automatically provided
    if you use any of the dependent fixtures.

    See tests/snapshot/test_snaphshot_downloads.py for an example of how
    you could use this fixture to have fine-grained control of the emulator.

    This makes an emulator available with the following default configuration:
    {
        "api": "31",
        "tag.id": "google_apis",
        "cpu": system_cpu()
    }

    You can provide your own avd configuration, by defining the variable
    avd_config = { ... } in your test module (i.e. test_xx.py)

    The avd_config should contain a dictionary with all the values that you
    would like to override in the config.ini that should be generated.

    You should provide at least the following parameters:

    - "api": The api level of the emulator you wish to run
    - "tag.id": The tag of the system image that should be used.

    The abi will be derived from the platform of the current running system.
    For x64 this will be x86_64 and for M1 this will be arm64_v8a

    This information will be used to obtain the system image:

    "system-images;android-{};{};{}".format(api, tag, abi)

    using sdkmanager that ships with the android sdk.

    For example, the default configuration mentioned above will result in the
    installation of the following avd:

    sdkmanager "system-images;android-31;google_apis;arm64-v8a"

    A created avd will remain running until all the tests completed, this means
    that multiple emulators can be running during a test run.

    At the end of the test run all the created emulators, and associated avds
    will be deleted.

    """
    avd_configs = json.loads(pytestconfig.getoption("avd_configs"))
    return await manage_emulator(
        request, pytestconfig, avd_configs[0] if avd_configs else {}, "emu-0"
    )


@pytest.fixture(scope="module")
async def emulators(request, pytestconfig) -> list[BaseEmulator]:
    """Makes multiple configured emulators available

    This fixture supports using multiple emulators and launches all configs
    inside avd_configs.

    'AvdId' field in each avd_config is required to distinguish between identical avds.

    Refer to emulator's docstring for implementation details on each emulator.
    """
    emulators = []
    avd_configs = json.loads(pytestconfig.getoption("avd_configs"))
    log_id = 0
    # Put a placeholder avd_config if none defined
    if not avd_configs:
        avd_configs.append({})
    for avd_config in avd_configs:
        emulators.append(
            await manage_emulator(request, pytestconfig, avd_config, f"emu-{log_id}")
        )
        log_id += 1
    return emulators


async def manage_emulator(
    request, pytestconfig, avd_param_config, log_id
) -> BaseEmulator:
    """Configures an emulator.

    Keeps track of a series of emulator objects, an Emulator boject
    is uniquely identified by its name. All its dependencies (system image, avd configuration)
    will be made available.

    Emulator objects are cached and could be in a running or stopped state.

    The device name is roughly as follows:

    ${api}_${tag_id}_${cpu}_${device_name}

    Args:
        request: Provide information on the executing test function.
        pytestconfig: pytest configuration information of the current test
        avd_pram_config: avd_config of the emulator specified by cfg files

    Returns:
        BaseEmulator: An emulator boject
    """

    avd_config = {
        "api": "31",
        "tag.id": "google_apis",
        "cpu": system_cpu(),
        "avd.ini.displayname": "°º¤ø,¸¸,ø¤º°`°º¤ø, UTF-8 ¸,ø¤°º¤ø,¸¸,ø¤º°`°º¤ø,¸",
        "device.name": "Pixel2",
    }
    avd_user_config = getattr(request.module, "avd_config", {})
    avd_config.update(avd_user_config)

    avd_config.update(avd_param_config)
    name = f"{avd_config['api']}_{avd_config['tag.id']}_{avd_config['cpu']}_{avd_config['device.name']}"
    if "AvdId" in avd_config:
        name += f"_{avd_config['AvdId']}"
    logging.info("--> Setting up emulator using avd config:%s", avd_config)

    if name not in pytest.emulators:
        if pytestconfig.getoption("debug_emulator") or not pytestconfig.getoption(
            "emulator"
        ):
            emu = DebugEmulator(
                android_home=Path(pytestconfig.getoption("android_home")),
                android_avd_home=Path(pytestconfig.getoption("android_avd_home")),
                logfile=pytestconfig.getoption("debug_emulator_log"),
            )
        else:
            logging.info("Launching %s", name)
            exe = Path(pytestconfig.getoption("emulator"))
            fetcher = pytestconfig.getoption("fetcher")
            emu = Emulator(
                android_home=Path(pytestconfig.getoption("android_home")),
                android_avd_home=Path(pytestconfig.getoption("android_avd_home")),
                exe=exe,
                avd_config=avd_config,
                fetcher=Path(fetcher) if fetcher else None,
                log_id=log_id,
            )

        emu.symbols = pytestconfig.getoption("symbols")
        emu.launch_flags = avd_config.get("launch_flags", [])
        pytest.emulators[name] = emu

    return pytest.emulators[name]


@pytest.fixture(scope="module")
@pytest.mark.async_timeout(200)
async def avd_launcher(emulator: BaseEmulator) -> BaseEmulator:
    """Makes a booted emulator accessible and with the animation apk installed.

    Note that the following holds:

    - This fixture has module scope, meaning an emulator will be launched only once
      per package

    - The emulator will be (re-)started if needed.

    Args:
        emulator (BaseEmulator): Test fixture that provides the configured emulator.

    Returns:
        BaseEmulator: A successfully booted emulator with the debug apk installed.
    """
    return await anext(manage_avd(emulator))


@pytest.fixture(scope="function")
@pytest.mark.async_timeout(200)
async def avd(
    do_not_display_nested_vm_warning, avd_launcher: BaseEmulator
) -> BaseEmulator:
    """Makes a booted emulator accessible and with the animation apk installed.

    This fixture has function scope, which will make sure the emulator will be
    restarted if it has crashed. A new emulator will be brought up once for each
    module.

    The emulator will be (re-)started if needed.

    Args:
        avd_launcher (BaseEmulator): Test fixture that provides the configured emulator.

    Returns:
        BaseEmulator: A successfully booted emulator with the debug apk installed.
    """
    if not avd_launcher.is_alive() or not avd_launcher.has_booted():
        logging.info("--> Restarting emulator")
        await avd_launcher.restart(avd_launcher.launch_flags)
        booted = await avd_launcher.wait_for_boot()
        if not booted:
            avd_launcher.stop()
            raise EmulatorFailedToBootException(
                "The emulator did not boot in time and was stopped."
            )
    else:
        logging.info("--> Reusing emulator")

    avd_launcher.reset_state()
    yield avd_launcher
    avd_launcher.reset_state()


@pytest.fixture(scope="module")
@pytest.mark.async_timeout(200)
async def avds(
    do_not_display_nested_vm_warning, emulators: list[BaseEmulator]
) -> list[BaseEmulator]:
    """Makes booted emulators accessible and with the animation apk installed.

    Note that the following holds:

    - This fixture has module scope, meaning an emulator will be launched only once
      per package

    - The emulator(s) will be (re-)started if needed.

    Args:
        emulators (list[BaseEmulator]): Test fixture that provides the configured emulator.

    Returns:
        List of BaseEmulator: Successfully booted emulators with the debug apk installed.
    """
    return await asyncio.gather(
        *[anext(manage_avd(emulator)) for emulator in emulators]
    )


async def manage_avd(emulator) -> BaseEmulator:
    """Helper to manage a booted emulator and make it available for avd and avds fixtures.

    Args:
        emulator (BaseEmulator): Test fixture that provides the configured emulator.

    Returns:
        BaseEmulator: A successfully booted emulator with the debug apk installed.
    """
    await emulator.restart(emulator.launch_flags)
    booted = await emulator.wait_for_boot()
    if not booted:
        await emulator.stop()
        raise EmulatorFailedToBootException(
            "The emulator did not boot in time and was stopped."
        )

    logging.info("The emulator has finished booting")

    # Note install appears to fail at times, b/324920328
    installed = await emulator.install_apk(
        APP_DEBUG_APK.absolute(), "com.google.AnimateBox"
    )
    if not installed:
        logging.warning(
            "The animation app failed to install, this can cause unexpected failures"
        )

    installed = await emulator.install_apk(
        APP_MOBLY_APK.absolute(), "com.google.android.mobly.snippet.bundled"
    )
    if not installed:
        logging.warning(
            "The mobly snippets failed to install, this can cause unexpected failures"
        )

    await emulator.reset_state()

    logging.info("--> yielding emulator")
    yield emulator

    logging.info("<-- teardown emulator")
    # Stop the emulator.
    await emulator.stop()
    logging.info("=== completed emulator")


@pytest.fixture
async def logcat(avd: BaseEmulator):
    adb_log_cmd = Command(
        [avd.adb.adb_binary, "-s", avd.adb.name, "logcat"],
        logging.getLogger(avd.log_id + "-logcat"),
    )
    await adb_log_cmd.run()
    yield adb_log_cmd.handler
    await adb_log_cmd.cancel()


@pytest.fixture
async def emulator_log(avd: BaseEmulator):
    """Returns the emulator log as a Queue (https://docs.python.org/3/library/queue.html)
    This contains the output seen on the console when the emulator is launched.

    The queue (log) will be emptied first.

    Usage:

    def test_logs_line(emulator_log):
        async for line in emulator_log:
           assert line == 'INFO    | Started GRPC server at 127.0.0.1:8554, security: Local, auth: none'
    """
    logging.info("--> emulator_log")
    assert avd.is_alive()

    if avd.log:
        avd.log.readlines()
    return avd.log


@pytest.fixture
def adb_shell(avd: BaseEmulator):
    """Function that invokes the adb executable with the given parameters.

    Usage:

    def test_sample(adb_shell):
        adb_shell("input keyevnet KEYCODE_WAKEUP")
    """
    assert avd.is_alive()
    return avd.adb.shell


@pytest.fixture
async def telnet(avd: BaseEmulator):
    """Access to the telnet console of the current emulator.

    Usage:

    def test_sample(telnet):
        telnet.send("event text")
    """
    assert avd.is_alive()
    return await avd.console()
