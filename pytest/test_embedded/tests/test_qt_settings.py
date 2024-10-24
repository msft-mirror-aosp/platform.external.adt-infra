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
"""Tests that we can read and write the emulator QSettings"""
import pytest

from emu.qt.emulator_settings import UISettings, CRASHREPORT_PREFERENCE_VALUE
from emu.qt.qt_settings import Status


@pytest.mark.flaky(reruns=0)
def test_emu_can_initialize_settings(emulator_qt_settings):
    assert emulator_qt_settings.status() == Status.NoError


@pytest.mark.flaky(reruns=0)
def test_emu_never_sends_crashes(emulator_qt_settings, never_upload_crashes):
    crash_settings = emulator_qt_settings[UISettings.CRASHREPORT_PREFERENCE]
    assert crash_settings == CRASHREPORT_PREFERENCE_VALUE.NEVER.value


@pytest.mark.flaky(reruns=0)
def test_emu_does_not_display_nested_vm_warning(
    emulator_qt_settings, do_not_display_nested_vm_warning
):
    nested_vm_warning = emulator_qt_settings[UISettings.SHOW_NESTED_WARNING]
    assert nested_vm_warning == "false"


@pytest.mark.flaky(reruns=0)
def test_can_read_and_write(
    emulator_qt_settings,
):
    emulator_qt_settings["Foo/Bar"] = "Bla"
    emulator_qt_settings.sync()
    emulator_qt_settings.load()
    assert emulator_qt_settings["Foo/Bar"] == "Bla"
