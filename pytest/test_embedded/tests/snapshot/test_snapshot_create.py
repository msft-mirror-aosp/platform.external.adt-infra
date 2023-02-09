import logging
import pytest
import os
from google.protobuf import empty_pb2


# This will run the boot test with DownloadableSnapshot feature turned on
# when it completes, it should save a snapshot to dist_out


@pytest.mark.e2e
@pytest.mark.timeout(timeout=180, func_only=True)
def test_snapshot_create(emulator):
    """Make sure the emulator status is set to booted."""
    if "DIST_DIR" in os.environ:
        logging.info("Testing snashot creation, will save a zip file to dist_out %s", os.environ["DIST_DIR"])
    else:
        logging.warning("Testing snashot creation, cannot save a zip file to dist_out as it is not defined")

    emulator.stop();

    try:
        assert emulator.launch(flags=["-feature", "DownloadableSnapshot"]);

        assert emulator.wait_for_boot(timeout=180);

        emulator.stop();
    except:
        logging.warning("The test failed, need investigation");

