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


@pytest.mark.vvl_testing
@pytest.mark.async_timeout(80)
async def test_vvl_error_in_host_logs_on_boot(avd, emulator_log):
    """Verifies that there are no vulkan validation errors in the host logs after boot."""
    if not await avd.wait_for_boot(timeout=60):
        pytest.fail("Emulator did not boot within 60 seconds.")

    # Wait for the system to settle down and produce logs.
    await asyncio.sleep(5)

    all_vvl_messages = []
    error_found = False

    APP_TAGS_FOR_ERROR_CHECKING = [
        "AEMU",
    ]
    VALIDATION_TAG = "VALIDATION"
    ERROR_TAG = "ERROR"
    # Read all available lines from the log queue without blocking.
    line_iterator = iter(emulator_log.readlines())
    for line in line_iterator:
        if VALIDATION_TAG in line:
            try:
                next_line = next(line_iterator)
                if any(app_tag in next_line for app_tag in APP_TAGS_FOR_ERROR_CHECKING):
                    all_vvl_messages.append(line.strip())
                    if ERROR_TAG in line:
                        error_found = True
            except StopIteration:
                # Reached end of file after VALIDATION_TAG, no next line to check
                pass

    # Always print VVL messages for debugging.
    if all_vvl_messages:
        logging.info(f"VVL messages found in host logs:\n" + "\n".join(all_vvl_messages))

    if error_found:
        pytest.fail(f"VVL errors found in host logs.\n")


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



@pytest.mark.vulkan_apps_gfxbench
@pytest.mark.async_timeout(300)
async def test_gfxbench_is_stable(gfxbench_app, avd, get_screenshot):
    """Verifies that the gfxbench sample app is running."""
    assert await gfxbench_app.is_running(), "Gfxbench application process not found"
    assert avd.is_alive()
    await asyncio.sleep(5) # wait for the app to start and check that it didn't crash
    assert avd.is_alive()
    await get_screenshot()


## These benchmarks will all create a <benchmark_name>.json file with frame times etc.
BENCHMARKS_TO_RUN = [
    "vulkan_5_high",
]

@pytest.mark.vulkan_apps_gfxbench
@pytest.mark.async_timeout(300)
@pytest.mark.parametrize("gfxbench_app", BENCHMARKS_TO_RUN, indirect=True)
async def test_gfxbench_run_benchmark(gfxbench_app, avd, get_screenshot):
    """Verifies that the gfxbench sample app is running."""
    assert await gfxbench_app.is_running(), "Gfxbench application process not found"
    await asyncio.sleep(5) # wait for the app to start
    assert avd.is_alive()
    await get_screenshot()
