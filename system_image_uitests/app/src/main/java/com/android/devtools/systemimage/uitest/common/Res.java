/*
 * Copyright (c) 2016 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.android.devtools.systemimage.uitest.common;

/**
 * Common resource IDs used to identify UI widgets by UiAutomator.
 * <p>
 * They could be String or regex String.
 */
public class Res {
    // System and Google application resource IDs ("com.android.*" or "com.google.*").

    public static final String BROWSER_BOOKMARKS_LABEL_RES = "com.android.browser:id/label";
    public static final String BROWSER_SEARCH_ICON_RES = "com.android.browser:/id/progress";
    public static final String BROWSER_URL_TEXT_FIELD_RES = "com.android.browser:id/url";
    public static final String BROWSER_TAB_SWITCHER_RES = "com.android.browser:id/tab_switcher";
    public static final String BROWSER_CLOSE_TAB_RES = "com.android.browser:id/closetab";

    public static final String CHROME_TERMS_ACCEPT_BUTTON_RES = "com.android.chrome:id/terms_accept";
    public static final String CHROME_SEARCH_BOX_RES = "com.android.chrome:id/search_box_text";
    public static final String CHROME_URL_BAR_RES = "com.android.chrome:id/url_bar";
    public static final String CHROME_MENU_BUTTON_RES = "com.android.chrome:id/menu_button";
    public static final String CHROME_MENU_BADGE_RES = "com.android.chrome:id/menu_badge";
    public static final String CHROME_SIGNIN_PROMO_ACCOUNT_RES = "com.android.chrome:id/signin_promo_choose_account_button";
    public static final String CHROME_SIGNIN_PROMO_CLOSE_RES = "com.android.chrome:id/signin_promo_close_button";
    public static final String CHROME_CLOSE_MENU_BUTTON_RES = "com.android.chrome:id/close_menu_id";
    public static final String CHROME_TITLE_RES = "com.android.chrome:id/title";
    public static final String CHROME_NO_THANKS_BUTTON_RES = "com.android.chrome\\d*:id" + "/(no_thanks_button|negative_button)";
    public static final String CHROME_PROGRESS_BAR_RES = "com.android.chrome:id/progress";
    public static final String CHROME_POSITIVE_BUTTON_RES = "com.android.chrome:id/positive_button";

    public static final String ANDROID_LAUNCHER_WELCOME_CLING_RES =
            "com.android.launcher\\d*:id/cling_dismiss";
    public static final String ANDROID_WELCOME_CLING_RES =
            "(com.android.launcher\\d*:id|com.google.android.googlequicksearchbox\\d*:id)"
                    + "/cling_dismiss_longpress_info";
    public static final String LAUNCHER_LIST_CONTAINER_RES =
            "(com.android.launcher\\d*:id|com.google.android.googlequicksearchbox\\d*:id|com.google.android.apps.nexuslauncher\\d*:id|com.android.launcher3\\d*:id/active)"
                    + "/(all_apps_container|all_apps_handle|apps_customize_pane_content|apps_list_view|drag_indicator)";
    public static final String LAUNCHER_LIST_DISMISS_RES = "com.google.android.apps.nexuslauncher:id/dismiss";
    public static final String CANCEL_SETUP_WIZARD_RES = "com.google.android.setupwizard:id/welcome_cancel_button";
    public static final String DEFERRED_SNOOZE_ITEM_RES = "com.google.android.setupwizard:id/deferred_snooze_item";
    public static final String ANDROID_PHONE_RES = "com.android.phone";
    public static final String ANDROID_SETTINGS_RES = "com.android.settings";
    public static final String ANDROID_SWITCH_TEXT_RES = "com.android.settings:id/switch_text";
    public static final String ABOUT_PHONE_LIST_CONTAINER_RES =
            "com.android.settings:id/container_material";
    public static final String APPS_LIST_CONTAINER_RES = "com.android.settings:id/list_container";
    public static final String APPS_TAB_CONTAINER_RES = "com.android.settings:id/pager";
    public static final String NETWORK_SWITCHES_RECYCLER_VIEW_RES =
            "com.android.settings:id/list";  // Added in API 24.
    public static final String SETTINGS_ADVANCED_OPTION_RES = "com.android.settings:id/advanced";
    public static final String SETTINGS_LIST_CONTAINER_RES =
            "(com.android.settings|android):id/(dashboard|list|dashboard_container|apps_list|main_content_scrollable_container|list_container)";
    public static final String Q_SETTINGS_LIST_CONTAINER_RES =
            "(com.android.settings|android):id/(main_content_scrollable_container)";
    public static final String SETTINGS_ACTION_BAR_RES = "com.android.settings:id/action_bar";

    public static final String CAMERA_FRAME_RES = "com.android.camera2:id/camera_app_root";
    public static final String CAMERA_SHUTTER_BUTTON_RES = "com.android.camera2:id/shutter_button";
    public static final String CAMERA_FILE_THUMBNAIL_RES = "com.android.camera2:id/rounded_thumbnail_view";
    public static final String CAMERA_FILE_DELETE_RES = "com.android.camera2:id/filmstrip_bottom_control_delete";
    public static final String PACKAGE_INSTALL_DONE_RES = "com.android.packageinstaller:id/done_button";
    public static final String LOCK_SCREEN_ICON_RES = "com.android.systemui:id/lock_icon";
    public static final String VPN_LOCK_ICON_RES = "com.android.systemui:id/vpn";
    public static final String NOTIFICATION_QUICK_PANEL_RES = "com.android.systemui:id/quick_qs_panel";
    public static final String NOTIFICATION_BAR_EXPAND_RES = "com.android.systemui:id/expand_indicator";
    public static final String NOTIFICATION_BAR_HEADER_RES = "com.android.systemui:id/header";
    public static final String MENU_LIST_RES = "com.android.documentsui:id/menu_list";
    public static final String OPTION_MENU_LIST_RES = "com.android.documentsui:id/option_menu_list";
    public static final String OPTION_MENU_SEARCH_RES = "com.android.documentsui:id/option_menu_search";

    public static final String GOOGLE_PLAY_VENDING_RES = "com.android.vending";
    public static final String GOOGLE_PLAY_IDLE_RES = "(com.android.vending:id/search_box_idle_text|com.android.vending:id/search_bar_hint)";
    public static final String GOOGLE_PLAY_ACTIVE_RES = "com.android.vending:id/search_box_active_text_view";
    public static final String GOOGLE_PLAY_INPUT_RES =
            "(com.android.vending:id/search_box_text_input|com.android.vending:id/search_bar_text_input)";
    public static final String GOOGLE_PLAY_LIST_TITLE_RES = "com.android.vending:id/li_title";
    public static final String GOOGLE_PLAY_FILTER_TOGGLE_RES = "com.android.vending:id/content_filter_on_off_toggle";
    public static final String GOOGLE_UNAUTHORIZED_SIGN_IN_RES = "com.android.vending:id/unauth_home_sign_in_button";
    public static final String GOOGLE_PLAY_ONBOARD_BUTTON_RES = "com.android.vending:id/play_onboard_center_button";

    public static final String DIALER_PHONE_RES = "(com.android.dialer\\d*:id|com.google.android.dialer\\d*:id)/(floating_action_button|fab)";
    public static final String DIALER_PAD_RES = "(com.android.dialer\\d*:id|com.google.android.dialer\\d*:id)/dialpad_floating_action_button";
    public static final String DIALER_DIGITS_RES = "(com.android.dialer\\d*:id|com.google.android.dialer\\d*:id)/digits";

    public static final String GOOGLE_SERVICES_NEXT_BUTTON_RES=
            "com.android.chrome:id/next_button";
    public static final String GOOGLE_SERVICES_ACCEPT_BUTTON_RES =
            "com.google.android.gms:id/next_button";
    public static final String NOW_SIGNIN_ACCEPT_BUTTON_RES =
            "com.google.android.googlequicksearchbox\\d*:id/accept_button";
    public static final String NOW_SIGNIN_DECLINE_BUTTON_RES =
            "com.google.android.googlequicksearchbox\\d*:id/decline_button";
    public static final String GOOGLE_BACKUP_SWITCH_RES =
            "com.google.android.gms:id/sud_items_switch";
    public static final String SIGN_IN_CONSENT_RES = "com.google.android.gms:id/signinconsentNext";

    public static final String SEARCH_TEXT_BOX =
            "(com.google.android.apps.maps:id|com.google.android.apps.gmm:id)" +
                    "/(search_omnibox_text_box|textbox|edit_textbox)";
    public static final String GOOGLE_AR_SNACKBAR_RES =
            "com.google.ar.core.examples.c.helloar:id/snackbar_text";

    // Third-party application resource IDs.
    public static final String APP_IMAGE_VIEW_ID =
            "com.example.android.rs.hellocompute:id/displayin";
    public static final String START_VPN_BUTTON_RES = "com.test.vpn:id/start_vpn";

    // Platform resource IDs ("android.*").
    public static final String ANDROID_DATE_PICKER_HEADER_RES = "android:id/date_picker_header";
    public static final String ANDROID_DATE_PICKER_HEADER_RES_19 = "android:id/datePicker";
    public static final String ANDROID_TIME_HEADER_RES = "android:id/time_header";
    public static final String ANDROID_TIME_HEADER_RES_19 = "android:id/timePicker";
    public static final String ANDROID_LIST_RES = "android:id/list";
    public static final String ANDROID_SETTING_LIST_RES = "com.android.settings:id/recycler_view";
    public static final String ANDROID_CONTENT_RES = "android:id/content";
    public static final String ANDROID_TITLE_RES = "android:id/title";
    public static final String ANDROID_SELECT_LIST = "android:id/select_dialog_listview";
    public static final String ANDROID_SUMMARY_RES = "android:id/summary";
    public static final String ANDROID_SWITCH_WIDGET = "android:id/switch_widget";
    public static final String ANDROID_ICON_RES = "android:id/icon";
    public static final String ANDROID_ERROR_CLOSE_RES = "android:id/aerr_close";

    // Android TV Resources.
    public static final String TV_LAUNCHER = "com.google.android.tvlauncher:id/button_icon";
    public static final String TV_MAIN_FRAME = "com.android.tv.settings:id/main_frame";
    public static final String TV_DATE_PICKER = "com.android.tv.settings:id/date_picker";
    public static final String TV_TIME_PICKER = "com.android.tv.settings:id/time_picker";
    public static final String TV_DISMISS = "com.google.android.tvlauncher:id/tray_dismiss";

    // Android Wear Resources.
    public static final String WEAR_SETTINGS = "com.google.android.apps.wearable.settings";
    public static final String WEAR_LAUNCHER = "com.google.android.wearable.app:id/launcher_view";
    public static final String WEAR_FACE_SETTINGS = "com.google.android.wearable.app:id/watchface_settings";
    public static final String WEAR_PREVIEW_IMAGE = "com.google.android.wearable.app:id/preview_image";
    public static final String WEAR_SHOW_ALL_BUTTON = "com.google.android.wearable.app:id/show_all_btn";
    public static final String WEAR_WATCH_FACE_PICKER =
            "com.google.android.wearable.app:id/watchface_picker_all_title";

    public static final String YOUTUBE_UPDATE_LATER_BUTTON_RES = "com.google.android.youtube:id/later_button";

    public static final String ADD_GOOGLE_ACC_WATCHER_PATTERN = "(?i)(not|accept|ok|cancel)(?-i)";
    public static final String API_DEMOS_WATCHER_PATTERN = "(?i)(thanks|no|continue)(?-i)";
    public static final String APP_WATCHER_PATTERN = "(?i)(ok|thanks)(?-i)";
    public static final String CAMERA_ACCESS_PERM_WATCHER_PATTERN = "(?i)(allow|next|got|continue|deny)(?-i)";
    public static final String GOOGLE_APP_CONF_WATCHER_PATTERN = "(?i).*(yes|accept|agree)(?-i)";
    public static final String GOOGLE_APP_CONT_WATCHER_PATTERN = "(?i)(continue|confirm|skip|next|accept)(?-i)";
    public static final String MAPS_WATCHER_PATTERN = "(?i)(accept|skip|got|ok|ride)(?-i)";
    public static final String NETWORK_UTIL_WATCHER_PATTERN = "(?i)(ok)(?-i)";
    public static final String PKG_INSTALL_WATCHER_PATTERN = "(?i)(new|decline)(?-i)";
    public static final String PLAY_STORE_WATCHER_PATTERN = "(?i)(ok|save)(?-i)";
    public static final String SETTINGS_WATCHER_PATTERN = "(?i)(ok)(?-i)";
    public static final String VPN_WATCHER_PATTERN = "(?i)(trust|ok)(?-i)";
}
