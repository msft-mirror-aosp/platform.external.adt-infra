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
"""Fixtures for launching an animation APK."""

import asyncio
import logging
import time
from pathlib import Path

import pytest

from emu.emulator import BaseEmulator
from emu.emulator_exceptions import (
    EmulatorFailedToBootException,
    FailedToInstallApkException,
)
from emu.application import (
    AnimationApplication,
    GearsApplication,
    GltfViewerApplication,
    HelloVKApplication,
    MapsDemoApplication,
    TriangleApplication,
    VulkanCapsViewerApplication,
    VulkanSamplesApplication,
    GfxbenchApplication,
)




@pytest.fixture
@pytest.mark.async_timeout(120)
async def install_animation_apk(request, avd: BaseEmulator):
    """Installs the animation APK on the emulator.

    Retries installation up to 3 times in case of transient failures.
    """
    local_run = request.config.getoption("--local_run")
    apk = AnimationApplication(avd, local_run)
    await apk.install()
    yield apk


@pytest.fixture
@pytest.mark.async_timeout(120)
async def animation_app(install_animation_apk, avd: BaseEmulator):
    """Launch the animation app that displays a rotating triangle.

    This fixture launches an application that displays a rotating
    triangle at 60fps, along with a white box in the corner.
    The application also logs all received key events to logcat.

    The animation app is stopped at the end of the test.

    Args:
        avd: An instance of the `BaseEmulator` class.

    Yields:
        None

    Raises:
        AssertionError: If the animation app fails to launch.
    """
    animation = install_animation_apk
    await animation.start()
    logging.info("--> yielding animation_app")
    yield animation
    logging.info("<-- teardown animation_app")

    await animation.stop()
    logging.info("=== finalized animation_app")

@pytest.fixture
@pytest.mark.async_timeout(120)
async def install_hellovk_apk(request, avd: BaseEmulator):
    """Installs the hellovk APK on the emulator.

    Retries installation up to 3 times in case of transient failures.
    """
    local_run = request.config.getoption("--local_run")
    apk = HelloVKApplication(avd, local_run)
    await apk.install()
    yield apk


@pytest.fixture
@pytest.mark.async_timeout(120)
async def hellovk_app(install_hellovk_apk, avd: BaseEmulator):
    """Launch the hellovk app that a triangle rendered with vulkan.

    Args:
        avd: An instance of the `BaseEmulator` class.

    Yields:
        None

    Raises:
        AssertionError: If the hellovk app fails to launch.
    """
    hellovk = install_hellovk_apk
    await hellovk.start()
    logging.info("--> yielding hellovk_app")
    yield hellovk
    logging.info("<-- teardown hellovk_app")

    await hellovk.stop()
    logging.info("=== finalized hellovk_app")

@pytest.fixture
@pytest.mark.async_timeout(120)
async def install_gears_apk(request, avd: BaseEmulator):
    """Installs the gears APK on the emulator."""
    local_run = request.config.getoption("--local_run")
    apk = GearsApplication(avd, local_run)
    await apk.install()
    yield apk


@pytest.fixture
@pytest.mark.async_timeout(120)
async def gears_app(install_gears_apk, avd: BaseEmulator):
    """Launch the gears app."""
    gears = install_gears_apk
    await gears.start()
    yield gears
    await gears.stop()


@pytest.fixture
@pytest.mark.async_timeout(120)
async def install_gltf_viewer_apk(request, avd: BaseEmulator):
    """Installs the gltf viewer APK on the emulator."""
    local_run = request.config.getoption("--local_run")
    apk = GltfViewerApplication(avd, local_run)
    await apk.install()
    yield apk


@pytest.fixture
@pytest.mark.async_timeout(120)
async def gltf_viewer_app(install_gltf_viewer_apk, avd: BaseEmulator):
    """Launch the gltf viewer app."""
    gltf_viewer = install_gltf_viewer_apk
    await gltf_viewer.start()
    yield gltf_viewer
    await gltf_viewer.stop()


@pytest.fixture
@pytest.mark.async_timeout(120)
async def install_maps_demo_apk(request, avd: BaseEmulator):
    """Installs the maps demo APK on the emulator."""
    local_run = request.config.getoption("--local_run")
    apk = MapsDemoApplication(avd, local_run)
    await apk.install()
    yield apk


@pytest.fixture
@pytest.mark.async_timeout(120)
async def maps_demo_app(install_maps_demo_apk, avd: BaseEmulator):
    """Launch the maps demo app."""
    maps_demo = install_maps_demo_apk
    await maps_demo.start()
    yield maps_demo
    await maps_demo.stop()


@pytest.fixture
@pytest.mark.async_timeout(120)
async def install_triangle_apk(request, avd: BaseEmulator):
    """Installs the triangle APK on the emulator."""
    local_run = request.config.getoption("--local_run")
    apk = TriangleApplication(avd, local_run)
    await apk.install()
    yield apk


@pytest.fixture
@pytest.mark.async_timeout(120)
async def triangle_app(install_triangle_apk, avd: BaseEmulator):
    """Launch the triangle app."""
    triangle = install_triangle_apk
    await triangle.start()
    yield triangle
    await triangle.stop()


@pytest.fixture
@pytest.mark.async_timeout(120)
async def install_vulkancapsviewer_apk(request, avd: BaseEmulator):
    """Installs the vulkancapsviewer APK on the emulator."""
    local_run = request.config.getoption("--local_run")
    apk = VulkanCapsViewerApplication(avd, local_run)
    await apk.install()
    yield apk


@pytest.fixture
@pytest.mark.async_timeout(120)
async def vulkancapsviewer_app(install_vulkancapsviewer_apk, avd: BaseEmulator):
    """Launch the vulkancapsviewer app."""
    vulkancapsviewer = install_vulkancapsviewer_apk
    await vulkancapsviewer.start()
    yield vulkancapsviewer
    await vulkancapsviewer.stop()


@pytest.fixture
@pytest.mark.async_timeout(300)
async def install_vulkan_samples_apk(request, avd: BaseEmulator):
    """Installs the vulkan samples APK on the emulator."""
    local_run = request.config.getoption("--local_run")
    apk = VulkanSamplesApplication(avd, local_run)
    await apk.install()
    yield apk


@pytest.fixture
@pytest.mark.async_timeout(120)
async def vulkan_samples_app(request, install_vulkan_samples_apk, avd: BaseEmulator):
    """Launch the vulkan samples app."""
    sample_name= request.param
    vulkan_samples = install_vulkan_samples_apk
    await vulkan_samples.ensure_assets(avd)
    await vulkan_samples.start(params=f"-e sample {sample_name}")
    yield vulkan_samples
    await vulkan_samples.stop()

@pytest.fixture
@pytest.mark.async_timeout(200)
async def coldboot_animation_app(emulator: BaseEmulator):
    """Launch the animation app after a cold boot.

    Similar to `animation_app`, but performs a cold boot before
    launching the application. This ensures that the application
    is launched in a clean state.

    Args:
        emulator: An instance of the `BaseEmulator` class.

    Yields:
        None

    Raises:
        EmulatorFailedToBootException: If the emulator fails to boot.
        AssertionError: If the animation app fails to launch.
    """
    logging.info("--> coldboot_animation_app")
    await emulator.stop()
    assert await emulator.launch(flags=["-no-snapshot-load"])
    booted = await emulator.wait_for_boot()
    if not booted:
        await emulator.stop()
        raise EmulatorFailedToBootException(
            "The emulator did not boot in time and was stopped."
        )

    assert emulator.is_alive()

    # Sleep for a few seconds after cold boot to allow
    # system UI to update (time, LTE signal, etc.).
    await asyncio.sleep(10)

    wait_for_animation_app_launch(emulator, timeout=30)
    logging.info("--> yielding coldboot_animation_app")
    yield
    logging.info("<-- teardown coldboot_animation_app")
    await emulator.stop_activity("com.google.AnimateBox")
    await emulator.reset_state()
    logging.info("== finalized coldboot_animation_app")


@pytest.fixture
@pytest.mark.async_timeout(120)
async def install_gfxbench_apk(request, avd: BaseEmulator):
    """Installs the gfxbench APK on the emulator."""
    local_run = request.config.getoption("--local_run")
    apk = GfxbenchApplication(avd, local_run)
    await apk.install()
    yield apk


@pytest.fixture
@pytest.mark.async_timeout(300)
async def gfxbench_app(request, install_gfxbench_apk, avd: BaseEmulator, log_directory):
    """Launch the gfxbench app."""
    benchmark_name = getattr(request, "param", None)
    gfxbench = install_gfxbench_apk
    await gfxbench.ensure_assets(avd)
    await gfxbench.start()

    if benchmark_name:
        play_time_s = 100  # 100 seconds
        play_time_ms = play_time_s*1000
        timeout_buffer_s = 20  # 20s buffer
        timeout_s = play_time_s + timeout_buffer_s

        # The app expects the test ids to be passed under the `test_ids` extra.
        logging.info(f"running {benchmark_name} for {play_time_ms} ms.")
        params = f'-e test_ids "{benchmark_name}" --ei raw_config.play_time {play_time_ms}'
        await avd.adb.clear_logcat()
        await gfxbench.start_as_broadcast(
            action="net.kishonti.testfw.ACTION_RUN_TESTS",
            receiver="net.kishonti.benchui.corporate.CommandLineSession",
            params=params
        )

        # Wait for the benchmark to complete by watching for the results file.
        results_dir = f"/storage/emulated/0/Android/data/{gfxbench.package_name}/files/results"
        try:
            await avd.adb.wait_for_path(f"{results_dir}/results.json", timeout_s)
        except asyncio.TimeoutError:
            pytest.fail("Timeout waiting for GFXBench benchmark to complete.")

        # Pull the results from the device.
        await avd.adb.pull(results_dir, str(log_directory))


    yield gfxbench
    await gfxbench.stop()
