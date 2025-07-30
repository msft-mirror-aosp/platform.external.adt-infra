import asyncio
from tests.fixtures.screen_recording_fixtures import *
from emu.application import VulkanSamplesApplication
import pytest


@pytest.mark.vulkan_apps
@pytest.mark.async_timeout(30)
async def test_run_hello_vk(
    hellovk_app, avd, get_screenshot
):
    """Verifies that the hellovk app is running.

    Args:
        hellovk_app: Fixture for the animation app.
        get_screenshot: Fixture to get a screenshot.
    """
    wait_time_s = 10
    await asyncio.sleep(wait_time_s)
    assert await hellovk_app.is_running(), f"HelloVK application process not found after {wait_time_s} seconds"
    assert avd.is_alive()
    await get_screenshot()


@pytest.mark.vulkan_apps
@pytest.mark.async_timeout(30)
async def test_run_gears(gears_app, avd, get_screenshot):
    """Verifies that the gears app is running."""
    wait_time_s = 10
    await asyncio.sleep(wait_time_s)
    assert await gears_app.is_running(), f"Gears application process not found after {wait_time_s} seconds"
    assert avd.is_alive()
    await get_screenshot()


@pytest.mark.vulkan_apps
@pytest.mark.async_timeout(30)
async def test_run_gltf_viewer(gltf_viewer_app, avd, get_screenshot):
    """Verifies that the gltf viewer app is running."""
    wait_time_s = 10
    await asyncio.sleep(wait_time_s)
    assert await gltf_viewer_app.is_running(), f"GLTF Viewer application process not found after {wait_time_s} seconds"
    assert avd.is_alive()
    await get_screenshot()


@pytest.mark.vulkan_apps
@pytest.mark.async_timeout(30)
async def test_run_maps_demo(maps_demo_app, avd, get_screenshot):
    """Verifies that the maps demo app is running."""
    wait_time_s = 10
    await asyncio.sleep(wait_time_s)
    assert await maps_demo_app.is_running(), f"Maps Demo application process not found after {wait_time_s} seconds"
    assert avd.is_alive()
    await get_screenshot()


@pytest.mark.vulkan_apps
@pytest.mark.async_timeout(30)
async def test_run_triangle(triangle_app, avd, get_screenshot):
    """Verifies that the triangle app is running."""
    wait_time_s = 10
    await asyncio.sleep(wait_time_s)
    assert await triangle_app.is_running(), f"Triangle application process not found after {wait_time_s} seconds"
    assert avd.is_alive()
    await get_screenshot()


@pytest.mark.vulkan_apps
@pytest.mark.async_timeout(30)
async def test_run_vulkancapsviewer(vulkancapsviewer_app, avd, get_screenshot):
    """Verifies that the vulkancapsviewer app is running."""
    wait_time_s = 10
    await asyncio.sleep(wait_time_s)
    assert await vulkancapsviewer_app.is_running(), f"Vulkan Caps Viewer application process not found after {wait_time_s} seconds"
    assert avd.is_alive()
    await get_screenshot()



SAMPLES_TO_TEST=[
    "hello_triangle",
    "hello_triangle_1_3",
    # "swapchain_images", #TODO: this requires assets
    "swapchain_recreation"
]

@pytest.mark.vulkan_apps_samples
@pytest.mark.async_timeout(300)
@pytest.mark.parametrize("vulkan_samples_app", SAMPLES_TO_TEST, indirect=True)
async def test_vulkan_samples(vulkan_samples_app, avd, get_screenshot):
    """Verifies that the vulkan samples app is running."""
    assert await vulkan_samples_app.is_running(), "Vulkan Samples application process not found"
    assert avd.is_alive()
    #Wait for the render to start (some samples are slower than others)
    await asyncio.sleep(5)
    await get_screenshot()
