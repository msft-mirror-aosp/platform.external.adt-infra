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
"""Fixtures for controlling the emulator QT settings, you usually want these to run before the emulator starts."""
import asyncio
import json
import logging
from pathlib import Path

import pytest
from emu.qt.qt_settings import QSettings

from emu.qt.emulator_settings import UISettings, CRASHREPORT_PREFERENCE_VALUE


@pytest.fixture
def emulator_qt_settings():
    ORG_NAME = "Android Open Source Project"
    ORG_DOMAIN = "com.android"
    APP_NAME = "Emulator"

    return QSettings(ORG_NAME, ORG_DOMAIN, APP_NAME)


@pytest.fixture
def never_upload_crashes(emulator_qt_settings):
    """Configure the emulator to never upload crashes."""
    emulator_qt_settings[UISettings.CRASHREPORT_PREFERENCE] = (
        CRASHREPORT_PREFERENCE_VALUE.NEVER.value
    )
    emulator_qt_settings.sync()


@pytest.fixture
def do_not_display_nested_vm_warning(emulator_qt_settings):
    emulator_qt_settings[UISettings.SHOW_NESTED_WARNING] = "false"
    emulator_qt_settings.sync()
