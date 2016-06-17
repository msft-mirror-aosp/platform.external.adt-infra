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
 * Common resource IDs.
 */
public class Res {
    public static final String LAUNCHER_LIST_CONTAINER_RES =
            "(com.android.launcher\\d*:id|com.google.android.googlequicksearchbox\\d*:id)"
                    + "/(all_apps_container|apps_customize_pane_content|apps_list_view)";
    public static final String SETTINGS_LIST_CONTAINER_RES =
            "(com.android.settings|android):id/(dashboard_container|list)";
    public static final String APPS_LIST_CONTAINER_RES = "com.android.settings:id/list_container";
    public static final String ABOUT_PHONE_LIST_CONTAINER_RES =
            "com.android.settings:id/container_material";
    public static final String ANDROID_WELCOME_CLING_RES =
            "(com.android.launcher\\d*:id|com.google.android.googlequicksearchbox\\d*:id)"
                    + "/cling_dismiss_longpress_info";
    public static final String ANDROID_LAUNCHER_WELCOME_CLING_RES =
            "com.android.launcher\\d*:id/cling_dismiss";
    public static final String GOOGLE_NOW_WELCOME_SKIP_RES =
            "com.google.android.googlequicksearchbox\\d*:id/decline_button";
    public static final String BROWSER_URL_TEXT_FIELD_RES = "com.android.browser:id/url";
    public static final String BROWSER_BOOKMARKS_LABEL_RES = "com.android.browser:id/label";
    public static final String ANDROID_DATE_PICKER_HEADER_RES = "android:id/date_picker_header";
    public static final String ANDROID_TIME_HEADER_RES = "android:id/time_header";
}
