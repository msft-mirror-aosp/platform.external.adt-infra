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
    // System and Google application resource IDs ("com.android.*" or "com.google.*")

    public static final String BROWSER_BOOKMARKS_LABEL_RES = "com.android.browser:id/label";
    public static final String BROWSER_SEARCH_ICON_RES = "com.android.browser:/id/progress";
    public static final String BROWSER_URL_TEXT_FIELD_RES = "com.android.browser:id/url";

    public static final String CHROME_TERMS_ACCEPT_BUTTON_RES = "com.android.chrome:id/terms_accept";
    public static final String CHROME_SIGN_IN_TITLE_RES = "com.android.chrome:id/signin_title";
    public static final String CHROME_NEGATIVE_BUTTON_RES = "com.android.chrome:id/negative_button";
    public static final String CHROME_SEARCH_BOX_RES = "com.android.chrome:id/search_box_text";
    public static final String CHROME_URL_BAR_RES = "com.android.chrome:id/url_bar";
    public static final String CHROME_CLOSE_MENU_BUTTON_RES = "com.android.chrome:id/close_menu_id";
    public static final String CHROME_BOOKMARKS_LABEL_RES = "com.android.chrome:id/title";
    public static final String CHROME_NO_THANKS_BUTTON = "com.android.chrome:id/no_thanks_button";

    public static final String ANDROID_LAUNCHER_WELCOME_CLING_RES =
            "com.android.launcher\\d*:id/cling_dismiss";
    public static final String ANDROID_WELCOME_CLING_RES =
            "(com.android.launcher\\d*:id|com.google.android.googlequicksearchbox\\d*:id)"
                    + "/cling_dismiss_longpress_info";
    public static final String LAUNCHER_LIST_CONTAINER_RES =
            "(com.android.launcher\\d*:id|com.google.android.googlequicksearchbox\\d*:id)"
                    + "/(all_apps_container|apps_customize_pane_content|apps_list_view)";

    public static final String ABOUT_PHONE_LIST_CONTAINER_RES =
            "com.android.settings:id/container_material";
    public static final String APPS_LIST_CONTAINER_RES = "com.android.settings:id/list_container";
    public static final String APPS_TAB_CONTAINER_RES = "com.android.settings:id/pager";
    public static final String NETWORK_SWITCHES_CONTAINER_RES =
            "com.android.settings:id/network_switches"; // Removed in API 24
    public static final String NETWORK_SWITCHES_RECYCLER_VIEW_RES =
            "com.android.settings:id/list"; // Added in API 24
    public static final String SETTINGS_ADVANCED_OPTION_RES = "com.android.settings:id/advanced";
    public static final String SETTINGS_LIST_CONTAINER_RES =
            "(com.android.settings|android):id/(dashboard|list)"; // Still present in API 24 but at a different point in the hierarchy.
    public static final String SETTINGS_RECYCLER_VIEW_RES =
            "com.android.settings:id/dashboard_container"; // Added in API 24

    public static final String LOCK_SCREEN_ICON_RES = "com.android.systemui:id/lock_icon";
    public static final String MOBILE_TYPE_ICONS_RES = "com.android.systemui:id/mobile_type";
    public static final String VPN_LOCK_ICON_RES = "com.android.systemui:id/vpn";
    public static final String WIFI_ICONS_RES = "com.android.systemui:id/wifi_signal";

    public static final String NOW_SIGNIN_ACCEPT_BUTTON_RES =
            "com.google.android.googlequicksearchbox\\d*:id/accept_button";
    public static final String NOW_SIGNIN_DECLINE_BUTTON_RES =
            "com.google.android.googlequicksearchbox\\d*:id/decline_button";
    public static final String NOW_SIGNIN_SCREEN_RES =
            "com.google.android.googlequicksearchbox\\d*:id/header_title";

    // Third-party application resource IDs
    public static final String APP_IMAGE_VIEW_ID =
            "com.example.android.rs.hellocompute:id/displayin";
    public static final String START_VPN_BUTTON_RES = "com.test.vpn:id/start_vpn";

    // Platform resource IDs ("android.*")
    public static final String ANDROID_DATE_PICKER_HEADER_RES = "android:id/date_picker_header";
    public static final String ANDROID_DATE_PICKER_HEADER_RES_19 = "android:id/datePicker";
    public static final String ANDROID_TIME_HEADER_RES = "android:id/time_header";
    public static final String ANDROID_TIME_HEADER_RES_19 = "android:id/timePicker";
    public static final String ANDROID_LIST_RES = "android:id/list";
}
