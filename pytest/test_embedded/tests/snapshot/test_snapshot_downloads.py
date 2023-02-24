import pytest
import requests
import logging

# This will run the tests in this module using this
# user configuration. This will fetch an image with api 33 and
# tag.id "google_apis"
#
# On M1 this will resolve to:  system-images;android-33;google_apis;arm64-v8a                                           | 5            | Google APIs ARM 64 v8a System Image
# On X64 this will resolve to: system-images;android-33;google_apis;x86_64
# avd_config = {"api": "33", "tag.id": "google_apis"}


@pytest.mark.e2e
@pytest.mark.skip(reason="flaky and not needed for now")
@pytest.mark.timeout(timeout=600, func_only=True)
def test_snapshot_download(emulator):
    """Make sure the emulator status is set to booted."""

    logging.info("Using %s", emulator)
    # Make sure this emulator is not running. Other tests might have been
    # using the same emulator.
    emulator.stop()

    # The emulator is not running any more..
    assert not emulator.is_alive()

    # Emulator is now in a ready to go state with a default avd_config, but it is not yet
    # running
    config = emulator.configuration

    # Inspect the hardware
    assert config.hardware["hw.keyboard"] == "yes"

    # Get the path
    assert config.directory.exists()

    # We now actually launch the emulator from a clean slate.
    assert emulator.launch(flags=["-wipe-data"])

    # The emulator kicks of its boot process, this should succeed
    assert emulator.wait_for_boot(timeout=420)

    # Stops the emulator.
    emulator.stop()

    # We should have created a default snapshot.
    assert (config.directory / "snapshots" / "default_boot").exists()
    assert (config.directory / "snapshots" / "default_boot" / "ram.bin").exists()
    assert (config.directory / "snapshots" / "default_boot" / "hardware.ini").exists()

    # Download the actual snapshot..
    # Note, this is currently fails..
    with pytest.raises(Exception):
        r = requests.get("https://my_downloadable_snapshot/ram.bin", stream=True)
        with open(
            config.directory / "snapshots" / "default_boot" / "ram.bin", "wb"
        ) as fd:
            for chunk in r.iter_content(chunk_size=4096):
                fd.write(chunk)

    # We now actually launch the emulator, without erasing it,
    assert emulator.launch()

    # The emulator kicks of its boot process, this should succeed
    assert emulator.wait_for_boot(timeout=180)
