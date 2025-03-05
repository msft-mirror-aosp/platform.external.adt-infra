# Copyright 2025 The Android Open Source Project
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

import pytest
import re
import logging
from aemu.proto.modem_service_pb2 import CellInfo
from aemu.proto.modem_service_pb2_grpc import ModemStub
from emu.timing import eventually
from google.protobuf import empty_pb2

__EMPTY__ = empty_pb2.Empty()

@pytest.fixture
def modem_controller(avd):
    """A gRPC stub to the modem controller."""
    try:
        ctrl = ModemStub(avd.channel)
        logging.info(f"Got {ctrl} response from modem controller.")
    except Exception as e:
        logging.error(f"An exception occurred: {e}")
        raise
    return ctrl

async def get_network_type(avd):
    """Retrieve the cellular network type from the telephony registry.

    Extracts the value of the `accessNetworkTechnology` field from
    the `NetworkRegistrationInfo` object that meets the following criteria:
    - `transportType` is WWAN (cellular network).
    - `domain` is CS (Circuit-Switched, used for voice/text services).

    Args:
        avd (BaseEmulator): The emulator instance.
    Returns:
        The cellular network type as a string, or None if no match is found.
    """
    mServiceState = await avd.adb.shell("dumpsys telephony.registry | grep mServiceState")
    pattern = (
        "NetworkRegistrationInfo{.*?domain=CS.*?transportType=WWAN.*?"
        "accessNetworkTechnology=(\\w+).*?}"
    )
    matches = re.findall(pattern, mServiceState)
    return matches[0] if len(matches) !=0 else None

@pytest.mark.parametrize(
    "network_standard,expected_type", [
        (CellInfo.CELL_STANDARD_GSM, "EDGE"),
        (CellInfo.CELL_STANDARD_UMTS, "HSPA"),
        (CellInfo.CELL_STANDARD_HSCSD, "EDGE"),
        (CellInfo.CELL_STANDARD_HSDPA, "HSPA"),
        (CellInfo.CELL_STANDARD_GPRS, "EDGE"),
        (CellInfo.CELL_STANDARD_LTE, "LTE"),
        (CellInfo.CELL_STANDARD_EDGE, "EDGE"),
        (CellInfo.CELL_STANDARD_FULL, "LTE"),
        (CellInfo.CELL_STANDARD_5G, "NR")
    ]
)


@pytest.mark.fast
@pytest.mark.async_timeout(120)
async def test_network_type_observable_from_registry(
        avd, modem_controller, network_standard, expected_type):
    """Verify that the cellular network type is observable from the telephony registry.

    Args:
        avd (BaseEmulator): The booted emulator instance.
        modem_controller (ModemStub): The modem controller gRPC stub.
        network_standard (CellStandard): The network standard to test.
        expected_type (str): The expected network type.

    Test steps:
        1. Launch a new AVD.
        2. Use the modem controller to change the network type to one of the following:
           - HSCD, GPRS, EDGE, UMTS, HSDPA, LTE, FULL, 5G (Verify 1).

    Verify:
        1. The new network type should be reflected in the telephony registry.
    """
    async def network_type_is_observable_from_registry():
        network_type = await get_network_type(avd)
        logging.info(f"Detected network type {network_type} (expected {expected_type})")
        return network_type == expected_type

    logging.info(f"Changing network emulation type to {expected_type} ...")
    await modem_controller.setCellInfo(CellInfo(cell_standard=network_standard))

    assert await eventually (
        network_type_is_observable_from_registry, timeout=60
    ), f"Couldn't observe network type '{expected_type}'"
