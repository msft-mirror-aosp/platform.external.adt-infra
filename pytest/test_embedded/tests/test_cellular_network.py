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
from functools import partial
from google.protobuf import empty_pb2
from functools import partial

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


@pytest.fixture
async def ensure_network_ready(avd):
    """Ensure the default emulator GSM network is ready"""
    async def _ensure_default_gsm_network_type():
        network_type = await avd.adb.shell("getprop gsm.network.type")
        return network_type.strip() == "LTE"
    if await eventually(_ensure_default_gsm_network_type, timeout=60):
        return # Success
    raise TimeoutError(
        f"Default GSM network type (LTE) not set."
    )


@pytest.mark.fast
@pytest.mark.async_timeout(120)
async def test_network_type_observable_from_registry(
    avd, modem_controller, ensure_network_ready):
    """Verify that the cellular network type is observable from the telephony registry.

    Args:
        avd (BaseEmulator): The booted emulator instance.
        modem_controller (ModemStub): The modem controller gRPC stub.
        ensure_network_ready: Ensures the default GSM network is ready.

    Test steps:
        1. Launch a new AVD.
        2. Use the modem controller to change the network type to one of the following:
           - HSCD, GPRS, EDGE, UMTS, HSDPA, LTE, FULL, 5G (Verify 1).

    Verify:
        1. The new network type should be reflected in the telephony registry.
    """
    async def network_type_is_observable_from_registry(expected_type):
        network_type = await get_network_type(avd)
        logging.info(f"Detected network type {network_type} (expected {expected_type})")
        return network_type == expected_type

    for network_standard, expected_type in [
        (CellInfo.CELL_STANDARD_GSM, "EDGE"),
        (CellInfo.CELL_STANDARD_UMTS, "HSPA"),
        (CellInfo.CELL_STANDARD_HSCSD, "EDGE"),
        (CellInfo.CELL_STANDARD_HSDPA, "HSPA"),
        (CellInfo.CELL_STANDARD_GPRS, "EDGE"),
        (CellInfo.CELL_STANDARD_LTE, "LTE"),
        (CellInfo.CELL_STANDARD_EDGE, "EDGE"),
        (CellInfo.CELL_STANDARD_FULL, "LTE"),
        (CellInfo.CELL_STANDARD_5G, "NR")
    ]:
        logging.info(f"Setting network emulation type to {expected_type} ...")
        await modem_controller.setCellInfo(CellInfo(cell_standard=network_standard))
        assert await eventually (
            partial(
                network_type_is_observable_from_registry,
                expected_type
            ),
            timeout=60
        ), f"Couldn't observe network type '{expected_type}'"


@pytest.mark.parametrize(
    "status,data_status", [
        ("HOME", CellInfo.CELL_STATUS_HOME),
        ("ROAMING", CellInfo.CELL_STATUS_ROAMING),
        ("NOT_REG_SEARCHING", CellInfo.CELL_STATUS_SEARCHING),
        ("DENIED", CellInfo.CELL_STATUS_DENIED),
    ]
)
@pytest.mark.fast
async def test_data_status_is_observable(avd, modem_controller, status, data_status):
    """Verify that cellular data status changes are observable through gRPC.

    Args:
        avd (BaseEmulator): The booted emulator instance.
        modem_controller (ModemStub): The modem controller gRPC stub.
        status (str): Label for the cellular data status.
        data_status (CellStatus): Cellular data status enumerated value.

    Test steps:
        1. Launch a new AVD.
        2. Set the cellular data status to one of the predefined values:
           HOME, ROAMING, NOT_REG_SEARCHING, DENIED (Verify 1).
    Verify:
        1. The cellular data status returned via gRPC matches the set status.
    """
    async def _has_data_status(data_status):
        cell_info = await modem_controller.getCellInfo(__EMPTY__)
        return cell_info.cell_status_data == data_status

    logging.info(f"Changing cellular data status to {status} ...")
    await modem_controller.setCellInfo(CellInfo(cell_status_data=data_status))

    assert await eventually (
        partial(_has_data_status, data_status), timeout=10
    ), f"Failed to set cellular data status to {status}"
