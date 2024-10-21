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
"""Fixtures for interacting with the emulator the gRPC endpoint."""
import pytest
from aemu.proto.emulator_controller_pb2_grpc import EmulatorControllerStub

from emu.emulator import BaseEmulator


@pytest.fixture
def emulator_controller(avd: BaseEmulator):
    """A grpc stub to the emulator controller.

    Usage:

    def test_sample(emulator_controller):
        response = await emulator_controller.getStatus(empty_pb2.Empty())
        assert response.booted
    """
    ctrl = EmulatorControllerStub(avd.channel)
    return ctrl


@pytest.fixture
def service(avd: BaseEmulator):
    """An async grpc stub to the emulator of the given type

    Usage:

    def test_sample(service):
        stub = service(SensorServiceStub)
        stub.method_call
    """

    def service(klazz):
        channel = avd.description.get_async_grpc_channel(
            [("emulator.security", "token")]
        )
        return klazz(channel)

    return service
