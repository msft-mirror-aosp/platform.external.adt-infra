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
import re
import pytest

from emu.timing import wait_until
from emu.emulator import BaseEmulator


@pytest.mark.embedded
@pytest.mark.async_timeout(60)
async def test_user_messages_on_logs(emulator: BaseEmulator):
    """Verify that the embedded emulator logs a USER_INFO message."""

    user_message_logged = False

    def user_message_filter(record):
        nonlocal user_message_logged
        text = r"USER_INFO\s+\|\s+Emulator is performing a full startup."
        message = record.getMessage()
        if re.match(text, message):
            user_message_logged = True
        return True

    emulator.logger.addFilter(user_message_filter)

    myflags = ["-no-snapshot", "-qt-hide-window"]
    await emulator.restart(emu_flags=myflags)

    # Note, this is usually logged in the first few seconds.
    assert wait_until(
        lambda: user_message_logged, timeout=60
    ), "We should have seen a message informing the emulator is doing a full startup."
