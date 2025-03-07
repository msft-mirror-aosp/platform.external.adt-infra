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

import pytest
import asyncio
import datetime
import logging
import random
from emu.timing import wait_until


FINGERPRINT_LABEL = {
    31: "Pixel Imprint",
    33: "Pixel Imprint",
    34: "Face & Fingerprint Unlock",
    35: "Fingerprint & Face Unlock"
}
PIN_UNLOCK_LABEL = {
    31: "Pixel Imprint + PIN",
    33: "PIN",
    34: "PIN • Face • Fingerprint",
    35: "PIN • Fingerprint • Face"
}

UI_WAIT_TIME = datetime.timedelta(seconds=30)

async def add_fingerprint(avd, ad_ui) -> int:
    """Add a new fingerprint to the emulator

    Args:
        avd (BaseEmulator): Fixture that gives access to the running emulator.
        ad_ui (UiDevice): Fixture that gives access to mobly's UiAutomator snippet.

    Steps:
        1. On the emulator, go to Settings > Security > Pixel Imprint.
        2. On the screen "Choose a screen lock", select PIN (or Pixel Imprint + PIN).
        3. Enter the 4-digit unlock PIN and click NEXT.
        4. Reenter PIN and click CONFIRM.
        5. On the "Lock screen" screen, click DONE.
        6. Scroll down on the "Set up Pixel Imprint" screen.
        7. Click I AGREE and wait for the "Touch the sensor" screen to appear.
        8. Use the emulator console to touch the fingerprint sensor.
        9. Repeat 8 until the screen "Lift, then touch again" is dismissed (Verify 1).

    Expected results:
        1. A prompt is displayed stating that a new fingerprint has been added.
           Settings > Security > 'Pixel Imprint' lists the newly added fingerprint.

    Returns:
        PIN: randomly generated fingerprint ID.
    """
    api = await avd.api_level()
    activity = "android.settings.SECURITY_SETTINGS"
    assert await avd.adb.shell(f"am start -W -a {activity}"), \
                                "Couldn't start Settings -> Security"

    if api >= 34:
        ad_ui(text="Checking device settings…",
              res="com.android.permissioncontroller:id/status_summary")\
             .wait.gone(UI_WAIT_TIME)

    security_label = "Security" if api <= 33 else "Security & privacy"
    security_frame = ad_ui(clazz="android.widget.FrameLayout", description=security_label)
    assert security_frame.wait.exists(UI_WAIT_TIME), "'Security' frame not found."

    if api >= 34:
        ad_ui(scrollable=True)\
            .scroll.down(text="Device unlock", res="android:id/title")
        ad_ui(text="Device unlock", res="android:id/title").click.wait(UI_WAIT_TIME)

    ad_ui(scrollable=True).scroll.down(text=FINGERPRINT_LABEL[api])
    ad_ui(text=FINGERPRINT_LABEL[api]).wait.click(UI_WAIT_TIME)
    ad_ui(text="Choose a screen lock").wait.exists()
    ad_ui(scrollable=True).scroll.down(text=PIN_UNLOCK_LABEL[api])
    ad_ui(text=PIN_UNLOCK_LABEL[api]).wait.exists()
    assert ad_ui(text=PIN_UNLOCK_LABEL[api]).click.wait(UI_WAIT_TIME)

    # Set unlock PIN and click NEXT.
    PIN = random.randint(0, 999)
    ad_ui(clazz='android.widget.EditText').set_text('{:04}'.format(PIN))
    next_button = ad_ui(text='NEXT', clazz='android.widget.Button')
    assert await wait_until(lambda: next_button.enabled)
    next_button.click.wait(UI_WAIT_TIME)

    # Reenter PIN and click CONFIRM.
    assert ad_ui(text="Re-enter your PIN").wait.exists(UI_WAIT_TIME)
    ad_ui(clazz='android.widget.EditText').set_text('{:04}'.format(PIN))
    confirm_button = ad_ui(text='CONFIRM', clazz='android.widget.Button')
    assert await wait_until(lambda: confirm_button.enabled)
    confirm_button.click.wait(UI_WAIT_TIME)

    assert ad_ui(text='DONE', clazz='android.widget.Button').wait.click(UI_WAIT_TIME)
    await asyncio.sleep(2)
    if api >= 34:
        ad_ui(scrollable=True).scroll.down(text="Pixel Imprint")
        assert ad_ui(text="Pixel Imprint").wait.click(UI_WAIT_TIME)
        await asyncio.sleep(2)
    ad_ui(scrollable=True).scroll.down()
    agree_button = ad_ui(text='I AGREE', clazz='android.widget.Button')
    agree_button.wait.exists(UI_WAIT_TIME)
    assert agree_button.click.wait(UI_WAIT_TIME)

    # Touch the fingerprint sensor
    logging.info(f"Attempt to touch the fingerprint sensor with fingerid {PIN}")
    touch_label = ad_ui(text='Touch the sensor', clazz="android.widget.TextView")
    assert touch_label.wait.exists(UI_WAIT_TIME)
    await asyncio.sleep(5)
    console = await avd.console()
    await console.send(f"finger touch {PIN}")

    lift_label = ad_ui(text='Lift, then touch again', clazz="android.widget.TextView")
    assert lift_label.wait.exists(UI_WAIT_TIME)
    while lift_label.exists:
        logging.info("Lifting and touching finger sensor again ..")
        await console.send(f"finger touch {PIN}")
        await asyncio.sleep(3)

    assert ad_ui(text="Fingerprint added",
                 clazz="android.widget.TextView").wait.exists(UI_WAIT_TIME)

    assert ad_ui(text='DONE', clazz='android.widget.Button').wait.click(UI_WAIT_TIME)
    logging.info(f"Added new fingerprint with fingerid {PIN}")

    return PIN


async def remove_fingerprint(avd, ad_ui, PIN):
    """Remove a fingerprint from the emulator.

    Args:
        avd (BaseEmulator): Fixture that gives access to the running emulator.
        ad_ui (UiDevice): Fixture that gives access to mobly's UiAutomator snippet.
        PIN (int): fingerprint ID.

    Steps:
        1. On the emulator, go to Settings > Security > Pixel Imprint.
        2. Enter the unlock PIN and click the enter key.
        3. On the "Pixel Imprint" screen, click the delete button, then,
           click "Yes, remove" (Verify 1).
    Expected results:
        1. The fingerprint named "Finger 1" no long exists on the
           "Pixel Imprint" screen.
    """
    api = await avd.api_level()
    ad_ui(scrollable=True).scroll.down(text=FINGERPRINT_LABEL[api])
    assert ad_ui(text=FINGERPRINT_LABEL[api]).wait.click(UI_WAIT_TIME)

    ad_ui(text="Re-enter your PIN", clazz="android.widget.TextView")\
         .wait.exists(UI_WAIT_TIME)

    ad_ui(clazz='android.widget.EditText').set_text('{:04}'.format(PIN))
    await asyncio.sleep(2)
    assert ad_ui.press('enter')

    if api >= 34:
        ad_ui(text="Pixel Imprint").wait.exists()
        ad_ui(scrollable=True).scroll.down(text="Pixel Imprint")
        assert ad_ui(text="Pixel Imprint").click.wait(UI_WAIT_TIME)

    assert ad_ui(res="com.android.settings:id/delete_button",
                 clickable=True).wait.click(UI_WAIT_TIME)
    await asyncio.sleep(2)
    assert ad_ui(text="Cancel", clazz="android.widget.Button")\
               .sibling(clazz="android.widget.Button").wait.click(UI_WAIT_TIME)

    # Confirm fingerprint was removed
    ad_ui(text="Pixel Imprint").wait.exists()
    assert not ad_ui.has(text="Finger 1")


@pytest.mark.fast
@pytest.mark.async_timeout(300)
async def test_fingerprint_unlock(avd, ad_ui):
    """Verify that a new fingerprint can be enrolled and used to unlock the emulator.

    avd (BaseEmulator): Fixture that gives access to the running emulator.
    ad_ui (uiDevice): Fixture that gives access to mobly's UiAutomator snippet.

    Test Steps:
        1. Launch a new AVD.
        2. Enroll a new fingerprint using the `add_fingerprint` method (Verify 1).
        3. Click on the power button twice to lock and wake up the emulator.
        4. Touch the fingerprint sensor with the enrolled fingerprint (Verify 2).
        5. Remove the fingerprint using the `remove_fingerprint` method (Verify 3).

    Verify:
        1. A prompt is displayed stating that a new fingerprint has been added.
           Settings > Security > 'Pixel Imprint' lists the newly added fingerprint.
        2. Emulator is unlocked, and the Security screen is displayed.
        3. The fingerprint is no longer listed on the "Pixel Imprint" screen.
    """
    api = await avd.api_level()

    # Add fingerprint
    logging.info("Attempting to add fingerprint ...")
    PIN = await add_fingerprint(avd, ad_ui)

    # Unlock device using the enrolled fingerprint
    logging.info("Attempting to unlock the device with the new fingerprint ...")
    console = await avd.console()
    await asyncio.sleep(5)
    ad_ui.press('power')
    await asyncio.sleep(5)
    ad_ui.press('power')
    assert ad_ui(res="com.android.systemui:id/lockscreen_opa").wait.exists()
    await console.send(f"finger touch {PIN}")

    # Verify the emulator is unlocked
    assert ad_ui(res="com.android.systemui:id/lockscreen_opa").wait.gone()

    # Remove fingerprint
    logging.info("Attempting to remove the fingerprint ...")
    await remove_fingerprint(avd, ad_ui, PIN)
