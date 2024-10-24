# Copyright 2024 - The Android Open Source Project
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
"""Contains all the known emulator settings.

Keep in sync with android/android-ui/modules/aemu-ui-widgets/src/android/skin/qt/qt-settings.h
"""

from enum import Enum


class CRASHREPORT_PREFERENCE_VALUE(Enum):
    """
    Enum for crash report preference values.

    This enum defines the possible values for the crash report preference setting.

    Members:
        ASK: Ask the user whether to send a crash report.
        ALWAYS: Always send crash reports automatically.
        NEVER: Never send crash reports.
    """

    ASK = 0
    ALWAYS = 1
    NEVER = 2


class UISettings:

    # Universal settings
    SHOW_ADB_WARNING = "showAdbWarning"
    SHOW_AVD_ARCH_WARNING = "showAvdArchWarning"
    SHOW_GPU_WARNING = "showGpuWarning"
    SHOW_VIRTUALSCENE_INFO = "showVirtualSceneInfo"
    SHOW_VGK_WARNING = "showVgkWarning"
    SHOW_HAXM_WARNING = "showHaxmWarning"
    SHOW_NESTED_WARNING = "showNestedWarning"
    ADB_PATH = "set/adbPath"
    AUTO_FIND_ADB = "set/autoFindAdb"
    ALWAYS_ON_TOP = "set/alwaysOnTop"
    FORWARD_SHORTCUTS_TO_DEVICE = "set/forwardShortcutsToDevice"
    FRAME_ALWAYS = "set/frameAlways4"
    SAVE_PATH = "set/savePath"
    UI_THEME = "set/theme"
    DISABLE_MOUSE_WHEEL = "set/disableMouseWheel"
    PAUSE_AVD_WHEN_MINIMIZED = "set/pauseAvdWhenMinimized"
    DISABLE_PINCH_TO_ZOOM = "set/disablePinchToZoom"
    BATTERY_CHARGE_LEVEL = "battery/charge_level"
    BATTERY_CHARGER_TYPE = "battery/charger_type"
    BATTERY_CHARGER_TYPE2 = "battery/charger_type2"
    BATTERY_HEALTH = "battery/health"
    BATTERY_STATUS = "battery/status"
    CELLULAR_NETWORK_TYPE = "cell/network_type"
    CELLULAR_SIGNAL_STRENGTH = "cell/signal_strength"
    CELLULAR_VOICE_STATUS = "cell/voice_status"
    CELLULAR_METER_STATUS = "cell/meter_status"
    CELLULAR_DATA_STATUS = "cell/data_status"
    MIC_INSERTED = "mic/inserted"
    MIC_AVAILABLE = "mic/available"
    MIC_ALLOW_READ_AUDIO = "mic/allow_real_audio"
    CRASHREPORT_PREFERENCE = "set/crashReportPreference"
    CRASHREPORT_SAVEPREFERENCE_CHECKED = "set/crashReportSavePreferenceChecked"
    GLESBACKEND_PREFERENCE = "set/glesBackendPreference"
    GLESAPILEVEL_PREFERENCE = "set/glesApiLevelPreference"
    CLIPBOARD_SHARING = "set/clipboardSharing"
    HTTP_PROXY_USE_STUDIO = "set/proxy/useStudio"
    HTTP_PROXY_TYPE = "set/proxy/type"
    HTTP_PROXY_HOST = "set/proxy/host"
    HTTP_PROXY_PORT = "set/proxy/port"
    HTTP_PROXY_AUTHENTICATION = "set/proxy/authentication"
    HTTP_PROXY_USERNAME = "set/proxy/username"
    DELETE_INVALID_SNAPSHOTS = "set/deleteInvalidSnapshots"
    LOCATION_PLAYBACK_FILE = "loc/playback_file_path"
    LOCATION_PLAYBACK_SPEED = "loc/playback_speed"
    LOCATION_RECENT_ALTITUDE = "loc/recent_altitude"
    LOCATION_RECENT_HEADING = "loc/recent_heading"
    LOCATION_RECENT_LATITUDE = "loc/recent_latitude"
    LOCATION_RECENT_LONGITUDE = "loc/recent_longitude"
    LOCATION_RECENT_VELOCITY = "loc/recent_velocity"
    RESIZABLE_SIZE = "resizable/size"
    SCREENREC_SAVE_PATH = "rec/savePath"


class AvdSettings:

    PER_AVD_SETTINGS_NAME = "/AVD.conf"
    SAVE_SNAPSHOT_ON_EXIT = "perAvd/set/saveSnapshotOnExit"
    PER_AVD_ALTITUDE = "perAvd/loc/altitude"
    PER_AVD_HEADING = "perAvd/loc/heading"
    PER_AVD_LONGITUDE = "perAvd/loc/longitude"
    PER_AVD_LATITUDE = "perAvd/loc/latitude"
    PER_AVD_VELOCITY = "perAvd/loc/velocity"
    PER_AVD_LOC_PLAYBACK_FILE = "perAvd/loc/playback_file_path"
    PER_AVD_LOC_PLAYBACK_SPEED = "perAvd/loc/playback_speed"
    PER_AVD_VIRTUAL_SCENE_POSTERS = "perAvd/virtualscene/posters"
    PER_AVD_VIRTUAL_SCENE_POSTER_SIZES = "perAvd/virtualscene/poster_sizes"
    PER_AVD_VIRTUAL_SCENE_TV_ANIMATION = "perAvd/virtualscene/tv_animation"
    PER_AVD_BATTERY_CHARGE_LEVEL = "perAvd/battery/charge_level"
    PER_AVD_BATTERY_CHARGER_TYPE2 = "perAvd/battery/charger_type2"
    PER_AVD_BATTERY_CHARGER_TYPE3 = "perAvd/battery/charger_type3"
    PER_AVD_BATTERY_HEALTH = "perAvd/battery/health"
    PER_AVD_BATTERY_STATUS = "perAvd/battery/status"
    PER_AVD_CELLULAR_NETWORK_TYPE = "perAvd/cell/network_type"
    PER_AVD_CELLULAR_SIGNAL_STRENGTH = "perAvd/cell/signal_strength"
    PER_AVD_CELLULAR_VOICE_STATUS = "perAvd/cell/voice_status"
    PER_AVD_CELLULAR_METER_STATUS = "perAvd/cell/meter_status"
    PER_AVD_CELLULAR_DATA_STATUS = "perAvd/cell/data_status"
    PER_AVD_MIC_INSERTED = "perAvd/mic/inserted"
    PER_AVD_MIC_AVAILABLE = "perAvd/mic/available"
    PER_AVD_MIC_ALLOW_READ_AUDIO = "perAvd/mic/allow_real_audio"
    PER_AVD_PAUSE_AVD_WHEN_MINIMIZED = "perAvd/set/pauseAvdWhenMinimized"
    PER_AVD_ENFORCE_KEYCODE_FORWARDING = "perAvd/set/enforceKeycodeForwarding"
    PER_AVD_RESIZABLE_SIZE = "perAvd/resizable/size"
