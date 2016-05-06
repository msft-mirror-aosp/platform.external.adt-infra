package com.android.devtools.systemimage.uitest.common;

/**
 * Common resource IDs.
 */
public class Res {
    public static final String LAUNCHER_LIST_CONTAINER_RES_REGEX =
            "(com.android.launcher\\d*:id|com.google.android.googlequicksearchbox\\d*:id)"
                    + "/(all_apps_container|apps_customize_pane_content|apps_list_view)";
    public static final String SETTINGS_LIST_CONTAINER_RES =
            "(com.android.settings|android):id/(dashboard_container|list)";
    public static final String APPS_LIST_CONTAINER_RES = "com.android.settings:id/list_container";
    public static final String ABOUT_PHONE_LIST_CONTAINER_RES =
            "com.android.settings:id/container_material";
    public static final String ANDROID_WELCOME_CLING_RES =
            "com.google.android.googlequicksearchbox:id/cling_dismiss_longpress_info";
    public static final String ANDROID_LAUNCHER_WELCOME_CLING_RES =
            "com.android.launcher:id/cling_dismiss";
    public static final String GOOGLE_NOW_WELCOME_SKIP_RES =
            "com.google.android.googlequicksearchbox:id/decline_button";
}
