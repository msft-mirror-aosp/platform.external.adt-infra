# -*- coding: utf-8 -*-
# Copyright 2022 The Android Open Source Project
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
"""Tests that the default configuration will attempt to retry the tests."""
import pytest
from emu.emulator_exceptions import EmulatorException

attempt = 0
fixture_attempt = 0
condition_callback_attempt = 0


@pytest.fixture
def first_force_retry():
    global fixture_attempt
    fixture_attempt += 1
    if fixture_attempt == 1:
        raise EmulatorException("Fixture failure, please try again!")


@pytest.mark.test_infra
def test_force_fixture_retry(first_force_retry):
    """Tests that if a fixture fails with an EmulatorException, it will be re-tried."""
    assert fixture_attempt == 2


@pytest.mark.test_infra
def test_force_retry():
    global attempt
    attempt += 1
    if attempt == 1:
        raise EmulatorException("Test failure, please try again!")

    assert attempt == 2


def condition_callback():
    """Note: This gets evaluated more than once!"""
    global condition_callback_attempt
    condition_callback_attempt += 1
    return True


@pytest.mark.flaky(delay=1, reruns=2, condition="condition_callback()")
def test_force_retry_condition():
    """Show cases how we could use a conditional_callback."""
    global condition_callback_attempt
    if condition_callback_attempt == 0:
        raise EmulatorException("Test failure, please try again!")

    assert condition_callback_attempt > 1


@pytest.fixture
def fail_on_first_execution(request):
    """Tests that request exposed execution_count"""
    if request.node.execution_count == 1:
        raise ValueError("Always fail on first")


@pytest.mark.flaky(delay=1, reruns=2)
def test_retry_item(fail_on_first_execution):
    assert True
