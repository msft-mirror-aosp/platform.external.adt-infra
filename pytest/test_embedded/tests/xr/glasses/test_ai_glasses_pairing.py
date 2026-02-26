import asyncio
import logging
import pytest

from emu.timing import eventually

# --- Constants ---
COMPANION_PKG = "com.google.android.glasses.companion"
GLASSES_CORE_PKG = "com.google.android.glasses.core"

INTENT_GET_PAIRING_STATE = "com.google.android.glasses.companion.GET_PAIRING_STATE"
INTENT_ASSISTED_PAIR = "com.google.android.glasses.companion.ASSISTED_PAIR"

BTN_POSITIVE_ID = "com.android.companiondevicemanager:id/btn_positive"
BTN_PERMISSION_ALLOW = "com.android.permissioncontroller:id/permission_allow_button"

REQUIRED_PERMISSIONS = [
    f"pm grant {COMPANION_PKG} android.permission.NEARBY_WIFI_DEVICES",
    f"pm grant {COMPANION_PKG} android.permission.BLUETOOTH_CONNECT",
    f"pm grant {COMPANION_PKG} android.permission.BLUETOOTH_SCAN",
    f"pm grant {COMPANION_PKG} android.permission.BLUETOOTH_ADVERTISE",
    f"pm grant {COMPANION_PKG} android.permission.ACCESS_FINE_LOCATION",
    f"pm grant {COMPANION_PKG} android.permission.ACCESS_COARSE_LOCATION",
    f"pm grant {COMPANION_PKG} android.permission.POST_NOTIFICATIONS",
    f"pm grant {GLASSES_CORE_PKG} android.permission.ACCESS_FINE_LOCATION",
]

# --- Helper Functions ---
async def is_boot_completed(emu):
    res = await emu.adb.shell("getprop sys.boot_completed")
    return res.strip() == "1"


async def is_companion_foreground(phone_emu):
    dump = await phone_emu.adb.shell("dumpsys window | grep mCurrentFocus")
    return COMPANION_PKG in dump


def setup_button_exists(phone_ui):
    try:
        return phone_ui(textContains="Set up glasses").exists
    except Exception as e:
        logging.warning(f"Failed to check UI: {e}")
        return False


async def is_pairing_state(phone_emu, expected_state):
    status_cmd = f"am broadcast -a {INTENT_GET_PAIRING_STATE} -p {COMPANION_PKG}"
    output = await phone_emu.adb.shell(status_cmd)
    return expected_state in output


async def dump_ui_hierarchy(phone_emu, filename="/data/local/tmp/uidump.xml"):
    """Helper to take a UI dump and log it for diagnostics."""
    await phone_emu.adb.shell(f"uiautomator dump {filename}")
    ui_dump = await phone_emu.adb.shell(f"cat {filename}")
    logging.info(f"UI Hierarchy ({filename}): {ui_dump}")


@pytest.mark.multi
@pytest.mark.xr
@pytest.mark.glasses
@pytest.mark.async_timeout(1080)
async def test_assisted_pair_cdm_association(avds, ad_ui_phone):
    """Test case to verify assisted pairing via CDM association."""
    assert len(avds) == 2, "Test requires exactly two emulators (Phone and Glasses)"

    phone_emu = avds[0]
    glasses_emu = avds[1]
    phone_ui = ad_ui_phone

    # 0. Wait for boot complete
    logging.info("Waiting for emulators to fully boot...")

    async def check_phone_boot():
        return await is_boot_completed(phone_emu)

    assert await eventually(
        check_phone_boot, timeout=120
    ), "Phone emulator did not boot in time"

    async def check_glasses_boot():
        return await is_boot_completed(glasses_emu)

    assert await eventually(
        check_glasses_boot, timeout=120
    ), "Glasses emulator did not boot in time"

    # 1. Grant permissions
    logging.info("Granting permissions on Phone emulator...")
    for perm_cmd in REQUIRED_PERMISSIONS:
        await phone_emu.adb.shell(perm_cmd)

    # 2. Get Glasses Bluetooth MAC
    logging.info("Retrieving Glasses Bluetooth MAC address...")
    mac_address_raw = await glasses_emu.adb.shell(
        "settings get secure bluetooth_address"
    )
    mac_address = mac_address_raw.strip()
    assert (
        mac_address
    ), "Failed to retrieve Bluetooth MAC address from Glasses emulator."
    logging.info(f"Glasses MAC Address: {mac_address}")

    # 3. Bring Companion to foreground (with retries)
    logging.info("Bringing Companion app to foreground...")

    async def check_foreground():
        return await is_companion_foreground(phone_emu)

    companion_launched = False
    for i in range(3):
        logging.info(f"Launching Companion app (Attempt {i+1})...")
        await phone_emu.adb.shell(
            f"monkey -p {COMPANION_PKG} -c android.intent.category.LAUNCHER 1"
        )
        if await eventually(check_foreground, timeout=15):
            logging.info("Companion app is in foreground.")
            companion_launched = True
            break
        logging.warning(f"Companion app failed to start on attempt {i+1}, retrying...")
        await asyncio.sleep(2)

    assert (
        companion_launched
    ), "Companion app failed to come to foreground after 3 attempts."

    logging.info("Waiting for 'Set up glasses' button to appear...")

    def check_setup_button():
        return setup_button_exists(phone_ui)

    if not await eventually(check_setup_button, timeout=60):
        logging.warning(
            "Timed out waiting for 'Set up glasses' button. Proceeding anyway."
        )

    logging.info("Waiting 10s before checking IDLE state...")
    await asyncio.sleep(10)

    # Wait for Pairing State to be IDLE
    logging.info("Waiting for pairing state to be IDLE...")

    async def check_pairing_idle():
        return await is_pairing_state(phone_emu, "IDLE")

    assert await eventually(
        check_pairing_idle, timeout=60
    ), "Pairing state did not reach IDLE."

    # 4. Initiate Association
    logging.info("Initiating ASSISTED_PAIR via broadcast...")
    pair_cmd = (
        f"am broadcast -a {INTENT_ASSISTED_PAIR} "
        f'--es "address" "{mac_address}" --ez "auto_cdm" true -p {COMPANION_PKG}'
    )
    await phone_emu.adb.shell(pair_cmd)

    # 4. Handle UI Permission Dialogs
    logging.info("Waiting for CDM 'Allow' dialog for Companion App...")

    async def wait_and_click_companion_cdm():
        try:
            # Check for Allow button immediately (first click)
            def btn_positive_exists():
                return phone_ui(resourceId=BTN_POSITIVE_ID).exists

            if btn_positive_exists():
                logging.info(f"Found Allow button ({BTN_POSITIVE_ID}). Clicking...")
                phone_ui(resourceId=BTN_POSITIVE_ID).click()

            # After expand, try checking/scrolling for Allow
            try:
                if phone_ui(scrollable=True).exists:
                    phone_ui(scrollable=True).scroll.to(resourceId=BTN_POSITIVE_ID)
            except Exception as scroll_e:
                logging.warning(f"Scroll failed (non-fatal): {scroll_e}")

            if btn_positive_exists():
                logging.info(
                    f"Found Allow button after expand ({BTN_POSITIVE_ID}). Clicking..."
                )
                phone_ui(resourceId=BTN_POSITIVE_ID).click()
                return True

            if phone_ui(resourceId=BTN_PERMISSION_ALLOW).exists:
                logging.info(
                    f"Found Allow button ({BTN_PERMISSION_ALLOW}). Clicking..."
                )
                phone_ui(resourceId=BTN_PERMISSION_ALLOW).click()
                return True

        except Exception as e:
            logging.warning(f"Error in wait_and_click_companion_cdm: {e}")
        return False

    if not await eventually(wait_and_click_companion_cdm, timeout=60):
        logging.error("Timed out waiting for 'Allow' dialog. Dumping diagnostics...")
        await dump_ui_hierarchy(phone_emu, "/data/local/tmp/uidump_companion.xml")
        raise TimeoutError("Timed out waiting for Allow dialog")

    logging.info("Waiting for 'Allow' CDM permission dialog for GlassesCore...")

    async def wait_and_click_glasses_core_cdm():
        try:
            await asyncio.sleep(10)
            if phone_ui(resourceId=BTN_PERMISSION_ALLOW).exists:
                logging.info(
                    f"Found Allow button ({BTN_PERMISSION_ALLOW}). Clicking..."
                )
                phone_ui(resourceId=BTN_PERMISSION_ALLOW).click()
                return True

            if phone_ui(resourceId=BTN_POSITIVE_ID).exists:
                logging.info(
                    f"Found Allow button after expand ({BTN_POSITIVE_ID}). Clicking..."
                )
                phone_ui(resourceId=BTN_POSITIVE_ID).click()
                return True

            # Fallback for safety
            if phone_ui(textContains="Allow").exists:
                logging.info("Found Allow button by text. Clicking...")
                phone_ui(textContains="Allow").click()
                return True
        except Exception as e:
            logging.warning(f"Error in wait_and_click_glasses_core_cdm: {e}")
        return False

    if not await eventually(wait_and_click_glasses_core_cdm, timeout=60):
        logging.error("Timed out waiting for 'Allow' dialog. Dumping diagnostics...")
        await dump_ui_hierarchy(phone_emu, "/data/local/tmp/uidump_pair.xml")
        raise TimeoutError("Timed out waiting for Pair dialog")

    # 5. Poll GET_PAIRING_STATE until PAIRED
    logging.info("Polling for pairing success...")

    async def check_pairing_successful():
        return await is_pairing_state(phone_emu, "PAIRED")

    assert await eventually(
        check_pairing_successful, timeout=60
    ), "Pairing did not complete successfully within timeout."
