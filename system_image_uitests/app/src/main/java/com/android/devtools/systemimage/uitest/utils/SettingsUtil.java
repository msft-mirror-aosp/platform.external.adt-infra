package com.android.devtools.systemimage.uitest.utils;

import android.app.Instrumentation;
import android.content.Context;
import android.content.res.AssetManager;
import android.graphics.Rect;
import android.os.Environment;
import androidx.test.uiautomator.By;
import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.UiObject;
import androidx.test.uiautomator.UiObject2;
import androidx.test.uiautomator.UiObjectNotFoundException;
import androidx.test.uiautomator.UiScrollable;
import androidx.test.uiautomator.UiSelector;
import android.util.Log;
import android.widget.Button;
import android.widget.Switch;

import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.watchers.watcher;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.util.concurrent.TimeUnit;

import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

public class SettingsUtil {
    public static final String TAG = SettingsUtil.class.getName();

    private SettingsUtil() {
        throw new AssertionError();
    }

    /**
     * Launches Settings and get the item list as a @{code UiScrollable}, ready to search for
     * clickable items.
     */
    private static UiScrollable launchAndGetItemList(
            Instrumentation instrumentation) throws Exception {
        AppLauncher.launch(instrumentation, "Settings");

        UiScrollable itemList = new UiScrollable(new UiSelector().resourceIdMatches(
                Res.SETTINGS_LIST_CONTAINER_RES));
        if (!itemList.waitForExists(TimeUnit.SECONDS.toMillis(5))) {
            itemList = new UiScrollable(new UiSelector().resourceIdMatches(
                    Res.LAUNCHER_LIST_CONTAINER_RES));
        }

        assertTrue("Failed to find the Settings items list.",
                itemList.waitForExists(TimeUnit.SECONDS.toMillis(5)));

        return itemList.setAsVerticalList();
    }

    /**
     * Launches Settings and find the item with the given name. Returns the item.
     */
    static UiObject findItem(Instrumentation instrumentation, String name) throws Exception {
        UiScrollable itemList = launchAndGetItemList(instrumentation);
        UiObject item = itemList.getChildByText(
                new UiSelector().className("android.widget.TextView"), name);

        assertTrue("Failed to find the item in Settings list.",
                item.waitForExists(TimeUnit.SECONDS.toMillis(5)));

        return item;
    }

    /**
     * Launches Settings and find the item with the given name. Returns the item.
     */
    static void findItem_v2(Instrumentation instrumentation) throws Exception {
        UiScrollable itemList = launchAndGetItemList(instrumentation);
        UiObject systemListItem = UiDevice.getInstance(instrumentation).findObject(
                new UiSelector().text("System"));
        if (systemListItem.waitForExists(5L)) {
            systemListItem.clickAndWaitForNewWindow();
        }
        UiObject item = itemList.getChildByText(
                new UiSelector().className("android.widget.TextView"), "Developer options");

        assertTrue("Failed to find the item in Settings list.",
                item.waitForExists(TimeUnit.SECONDS.toMillis(5)));

    }

    /**
     * Launches Settings and launch the item with the given name. Returns the result of the call.
     */
    public static boolean openItem(
            Instrumentation instrumentation, String name) throws Exception {
        return findItem(instrumentation, name).clickAndWaitForNewWindow();
    }

    /**
     * Activate "Sample Device Admin" policy under Device administrators.
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param adminName       admin policy name
     * @throws Exception if it fails to find a UI widget.
     */
    public static void activate(Instrumentation instrumentation, String adminName,
                                String text1, String text2)
            throws Exception {
        changePolicyActivation(instrumentation, adminName, "Activate",
                text1, text2);
    }

    /**
     * Deactivate "Sample Device Admin" policy under Device administrators.
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param adminName       admin policy name
     * @throws Exception if it fails to find a UI widget.
     */
    public static void deactivate(Instrumentation instrumentation, String adminName,
                                  String text1, String text2)
            throws Exception {
        changePolicyActivation(instrumentation, adminName, "Deactivate",
                text1, text2);
    }

    public static void launchDeviceAdminApps(Instrumentation instrumentation,
                                             String text1, String text2) throws Exception {
        SettingsUtil.openItem(instrumentation, text1);

        UiScrollable itemList =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)
                );
        itemList.setAsVerticalList();
        // Go to device administrators page.
        itemList.getChildByText(new UiSelector().className("android.widget.TextView"),
                text2).clickAndWaitForNewWindow();
    }

    private static void changePolicyActivation(
            Instrumentation instrumentation, String adminName, String change,
            String text1, String text2) throws Exception {

        UiDevice device = UiDevice.getInstance(instrumentation);
        launchDeviceAdminApps(instrumentation, text1, text2);

        // Select admin option to activate/deactivate.
        device.findObject(new UiSelector().text(adminName)).clickAndWaitForNewWindow();
        UiObject scrollView = device.findObject(
                new UiSelector().className("android.widget.ScrollView"));

        scrollView.waitForExists(TimeUnit.SECONDS.toMillis(3L));

        // Scroll to the end to see Activate/Deactivate button.
        Rect labelRect = scrollView.getBounds();
        device.swipe(
                labelRect.centerX(),
                labelRect.centerY(),
                labelRect.centerX(),
                labelRect.top,
                10);


        UiObject actionButton = device.findObject(
                new UiSelector().resourceId(Res.SETTINGS_ACTION_BUTTON_RES));

        actionButton.waitForExists(TimeUnit.SECONDS.toMillis(3L));

        String[] words = actionButton.getText().split("[\\s\\xA0]+");
        // Do not proceed if policy value matches the requested value.
        if (!words[0].equalsIgnoreCase(change)) {
            Log.w(TAG, "changePolicyActivation: policy already set as requested");
            return;
        }

        if (change.equalsIgnoreCase("Activate")) {
            actionButton.clickAndWaitForNewWindow();
            return;
        }
        // Only for deactivation: For deactivation and extra alert box is displayed.
        actionButton.click();
        UiObject okButton = device.findObject(new UiSelector().text("OK"));
        okButton.waitForExists(TimeUnit.SECONDS.toMillis(3L));
        okButton.clickAndWaitForNewWindow();
    }

    /**
     * Fetch permissions settings for a given application type.
     * For API <= 26
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param appType         String describing the application type, as listed on the App permissions
     *                        screen.
     * @throws Exception if it fails to find a UI object.
     */
    public static boolean getAppPermissions_v1(
            Instrumentation instrumentation, String appType, String appText)
            throws Exception {

        UiDevice device = UiDevice.getInstance(instrumentation);

        SettingsUtil.openItem(instrumentation, appText);
        UiObject appPermissions = device.findObject(new UiSelector().text("App permissions"));
        if (appPermissions.waitForExists(5L)) {
            appPermissions.clickAndWaitForNewWindow();
        }
        UiScrollable appPermissionsList = new UiScrollable(
                new UiSelector().resourceId(Res.ANDROID_CONTENT_RES));

        if (appPermissionsList.waitForExists(200L)) {
            appPermissionsList.getChildByText(
                    new UiSelector().className("android.widget.TextView"), appType)
                    .clickAndWaitForNewWindow();
        } else {
            throw new UiObjectNotFoundException("Failed to find the item in Apps.");
        }

        UiObject appPermissionsLabel = device.findObject(
                new UiSelector()
                        .textMatches("(?i)" + appType + "\\spermissions(?-i)")
        );
        boolean hasAppPermissionsLabel = appPermissionsLabel.waitForExists(5L);
        if (hasAppPermissionsLabel) {
            appPermissionsLabel.clickAndWaitForNewWindow();
        }

        return hasAppPermissionsLabel;
    }

    /**
     * Fetch permissions settings for a given application type.
     * For API > 26
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param appType         String describing the application type, as listed on the App permissions
     *                        screen.
     * @throws Exception if it fails to find a UI object.
     */
    public static UiObject getAppPermissions_v2(
            Instrumentation instrumentation, String appType, String appText, String permissionText)
            throws Exception {

        UiDevice device = UiDevice.getInstance(instrumentation);

        if (SystemUtil.getApiLevel() <= 32) {
            SettingsUtil.openItem(instrumentation, appText);
            SettingsUtil.clickAdvancedMenu(device);
        } else {
            AppLauncher.launchPath(instrumentation, true, "Settings", appText);
        }

        UiObject seeAllApps = device.findObject(new UiSelector()
                .textContains("See all"));

        if (seeAllApps.waitForExists(5000L)) {
            seeAllApps.clickAndWaitForNewWindow();
        } else {
            seeAllApps = device.findObject(new UiSelector()
                    .textContains("All apps"));
            if (seeAllApps.exists()) {
                seeAllApps.clickAndWaitForNewWindow();
            }
        }

        UiScrollable appPermissionsList = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_CONTENT_RES));

        if (SystemUtil.getApiLevel() < 31) {
            UiSelector permissionsSelector = new UiSelector().text(permissionText);
            UiObject appPermissionsLabel = device.findObject(permissionsSelector);
            boolean hasAppPermissionsLabel = appPermissionsLabel.waitForExists(5L);
            if (hasAppPermissionsLabel) {
                appPermissionsLabel.clickAndWaitForNewWindow();
            } else if (appPermissionsList.waitForExists(TimeUnit.SECONDS.toMillis(60L))) {
                appPermissionsList.setAsVerticalList();
                if (appPermissionsList.scrollIntoView(permissionsSelector)) {
                    device.findObject(permissionsSelector).clickAndWaitForNewWindow();
                }
            }
        }
        if (appPermissionsList.waitForExists(TimeUnit.SECONDS.toMillis(60L))) {
            appPermissionsList.setAsVerticalList();
            UiSelector appSelector = new UiSelector().text(appType);
            if (appPermissionsList.scrollIntoView(appSelector)) {
                return device.findObject(appSelector);
            }
        }

        throw new UiObjectNotFoundException(
                "Failed to find the item " + (appType) + ":" + (appText) + " in App permissions.");
    }

    /**
     * Fetch permissions settings for a given application type.
     * For API = 26
     *
     * @param appType String describing the application type, as listed on the App permissions
     *                screen.
     * @throws Exception if it fails to find a UI object.
     */

    public static boolean getAppPermissions_v3(String appType)
            throws Exception {

        UiScrollable appPermissionsList = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_CONTENT_RES));
        if (appPermissionsList.waitForExists(TimeUnit.SECONDS.toMillis(20))) {
            return appPermissionsList.getChildByText(
                    new UiSelector().className("android.widget.TextView"), appType).exists();
        } else {
            throw new UiObjectNotFoundException("Failed to find the item in Apps.");
        }
    }

    /**
     * Enable or disable permissions settings for a given application type
     * For API <= 25
     *
     * @param instrumentation   see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                          getInstrumentation}
     * @param appType           String describing the application type, as listed on the App permissions
     *                          screen.
     * @param appName           String describing the application name, as listed on the {appType}
     *                          permissions screen.
     * @param enablePermissions boolean indicating whether the permissions should be enabled
     *                          or disabled.
     * @throws Exception if it fails to find a UI object.
     */
    public static void setAppPermissions_v1(
            Instrumentation instrumentation, String appType,
            String appName, boolean enablePermissions,
            String denyButtonText, String appText)
            throws Exception {

        UiDevice device = UiDevice.getInstance(instrumentation);

        getAppPermissions_v1(instrumentation, appType, appText);

        UiObject2 permissionsBtn = UiAutomatorPlus.findObjectByRelative(
                instrumentation,
                By.clazz("android.widget.Switch"),
                By.text(appName),
                By.clazz("android.widget.LinearLayout"),
                2);

        if (!permissionsBtn.isChecked() && enablePermissions)
            permissionsBtn.click();

        else if ((permissionsBtn.isChecked() && !enablePermissions)) {
            permissionsBtn.click();

            final UiObject denyButton = device.findObject(new UiSelector().text(denyButtonText));

            try {
                boolean dialogLaunched = new Wait().until(denyButton::exists);
                if (dialogLaunched)
                    denyButton.click();
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    /**
     * Enable or disable permissions settings for a given application type
     * For API >= 28
     *
     * @param instrumentation   see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                          getInstrumentation}
     * @param appType           String describing the application type, as listed on the App permissions
     *                          screen.
     * @param appName           String describing the application name, as listed on the {appType}
     *                          permissions screen.
     * @param denyButtonLabel   String describing the text label on the deny permissions button.
     *
     * @param appsLocation      String describing the location of Settings -> Apps & notifications.
     *
     * @param permissionText
     *
     * @throws Exception if it fails to find a UI object.
     */
    public static void setAppPermissions_v2(
            Instrumentation instrumentation, String appType, String appName,
            String denyButtonLabel, String appsLocation,
            String permissionText)
            throws Exception {

        UiDevice device = UiDevice.getInstance(instrumentation);

        getAppPermissions_v2(instrumentation, appType, appsLocation, permissionText);

        device.findObject(new UiSelector().text(appType)).click();

        UiObject permissions = device.findObject(
                new UiSelector().resourceId(Res.ANDROID_TITLE_RES).text("Permissions"));

        if (permissions.waitForExists(3000L)) {
            permissions.clickAndWaitForNewWindow();
        }
        UiScrollable permissionList = new UiScrollable(new UiSelector().
                resourceId(Res.ANDROID_LIST_RES).
                packageName(Res.PACKAGE_INSTALLER_RES));

        UiObject appPermission = device.findObject(
                new UiSelector().text(appName).resourceId(Res.ANDROID_TITLE_RES));
        if (permissionList.waitForExists(3000L)) {
            assertTrue("Could not find " + appPermission + " in permissions list",
                    permissionList.scrollIntoView(appPermission));
        }
        appPermission.clickAndWaitForNewWindow();

        UiObject permissionsButton = device.findObject(
                new UiSelector().text(denyButtonLabel));

        if (permissionsButton.waitForExists(3000L)) {
            permissionsButton.clickAndWaitForNewWindow();
        }
    }

    /**
     * Enable or disable permissions settings for a given application type
     * For API >= 29
     *
     * @param instrumentation   see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                          getInstrumentation}
     * @param appType           String describing the application type, as listed on the App permissions
     *                          screen.
     * @param appName           String describing the application name, as listed on the {appType}
     *                          permissions screen.
     * @param enablePermissions boolean indicating whether the permissions should be enabled
     *                          or disabled.
     * @throws Exception if it fails to find a UI object.
     */
    public static void setAppPermissions_v3(
            Instrumentation instrumentation, String appType,
            String appName, boolean enablePermissions,
            String denyButtonText, String appText,
            String permissionText)
            throws Exception {

        String targetApp = SystemUtil.getApiLevel() >= 31 ? appName : appType;
        UiDevice device = UiDevice.getInstance(instrumentation);

        getAppPermissions_v2(instrumentation, targetApp, appText, permissionText);

        device.findObject(new UiSelector().text(targetApp)).click();

        if (SystemUtil.getApiLevel() <= 30) {
            UiScrollable permissionList = new UiScrollable(new UiSelector().resourceId(Res.PERMISSION_RECYCLER_VIEW));

            UiObject appButton = SystemUtil.getApiLevel() == 30 ?
                    permissionList.getChildByText(new UiSelector().className("android.widget.TextView").index(0), appName) :
                    permissionList.getChildByText(new UiSelector().className("android.widget.TextView"), appName);

            if (appButton.exists()) {
                appButton.click();
            }

            UiObject permissionsAllowBtn = device.findObject(
                    new UiSelector().resourceIdMatches(Res.ALLOW_PERMISSION_BUTTON));
            UiObject permissionsDenyBtn = device.findObject(
                    new UiSelector().resourceId(Res.DENY_PERMISSION_BUTTON));

            if (enablePermissions) {
                permissionsAllowBtn.click();
            } else if ((permissionsAllowBtn.isChecked())) {
                permissionsDenyBtn.click();

                final UiObject denyButton = device.findObject(new UiSelector().text(denyButtonText));

                try {
                    boolean dialogLaunched = new Wait().until(denyButton::exists);
                    if (dialogLaunched) {
                        denyButton.click();
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }
    }

    /**
     * Scroll the view to a target element in a given region.
     * @param device UiDevice
     * @param region UiSelector
     * @param target UiSelector
     * @return boolean
     */
    public static boolean scrollToObject(UiDevice device, UiSelector region, UiSelector target) {
        try {
            UiScrollable scrollable = new UiScrollable(region);
            scrollable.setAsVerticalList();

            UiScrollable itemList = new UiScrollable(region);
            itemList.setAsVerticalList();
            itemList.scrollIntoView(target);

            int attempts = 0;
            final int maxAttempts = 5;
            final long waitTime = 5000;
            boolean targetExists;
            do {
                targetExists = new Wait(waitTime).until(() -> device.findObject(target).exists());
                attempts++;
            } while (!targetExists && attempts < maxAttempts);
            if (!targetExists) {
                Log.w(TAG, "Failed to scroll to the target object");
                return false;
            }
        } catch (Exception e) {
            Log.e(TAG, "Exception occurred while trying to scroll to the target object", e);
            throw new RuntimeException("Failed to scroll to the target object due to an exception", e);
        }
        return true;
    }

    /*
     * Helper function to click "Advanced" is setting menu if it exists.
     * Otherwise it should do nothing and should not throw any exception.
     */
    public static void clickAdvancedMenu(UiDevice device) {
        UiScrollable itemList =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)
                );

        try {
            itemList.setAsVerticalList();
            UiSelector advancedButton = new UiSelector().text("Advanced");
            if (itemList.scrollIntoView(advancedButton)) {
                device.findObject(advancedButton).click();
            }
        } catch (UiObjectNotFoundException e) {
            Log.w(TAG, "Advanced does not exist");
        }
    }

    /**
     * Common code for finding a checkbox/switch in the Date & time settings.
     */
    public static UiObject2 navigateToDateTimeSwitch(String text, Instrumentation instrumentation, String container) {
        try {
            return UiAutomatorPlus.findObjectByRelative(
                    instrumentation,
                    By.clazz("android.widget.Switch"),
                    By.text(text),
                    By.res(container));
        } catch (UiObjectNotFoundException e1) {
            try {
                return UiAutomatorPlus.findObjectByRelative(
                        instrumentation,
                        By.clazz("android.widget.CheckBox"),
                        By.text(text),
                        By.res(container));
            } catch (UiObjectNotFoundException e2) {
                fail("Could not find Date Time switch");
            }
        }
        return null;
    }

    public static UiObject findObjectByRelative(UiScrollable verticalList, String childText, String classType) throws Exception {
        UiObject uiObject = verticalList.getChildByText(new UiSelector().className(classType), childText);
        return uiObject.getChild(new UiSelector().className(Switch.class.getName()));
    }

    public static void setCameraEnabled(final boolean enableCameraDevices, Instrumentation instrumentation, final UiDevice device) throws Exception {
        boolean isAPIDemoInstalled = PackageInstallationUtil.isPackageInstalled(instrumentation,
                "com.example.android.apis");

        if (isAPIDemoInstalled) {
            AppLauncher.launch(instrumentation, "API Demos");

            final UiObject appLabel = device.findObject(new UiSelector().text("App"));
            if (new Wait().until(appLabel::exists)) {
                appLabel.click();
            }

            final UiObject deviceAdminLabel = device.findObject(new UiSelector().text("Device Admin"));
            if (new Wait().until(deviceAdminLabel::exists)) {
                deviceAdminLabel.click();
            }

            final UiObject generalLabel = device.findObject(new UiSelector().text("General"));
            if (new Wait().until(generalLabel::exists)) {
                generalLabel.click();
            }

            final UiObject enableCamerasCheckbox = device.findObject(
                    new UiSelector().text(enableCameraDevices ? "Device cameras disabled" :
                            "Device cameras enabled"));
            if (new Wait().until(enableCamerasCheckbox::exists)) {
                enableCamerasCheckbox.click();
            }
            device.pressBack();
            device.pressBack();
            device.pressBack();
            device.pressBack();
            device.pressHome();
        } else {
            Log.w(TAG, "setCameraEnabled: required APK is missing");
        }
    }


    public static boolean verifyCameraAppDisabled(Instrumentation instrumentation) throws Exception {
        AppLauncher.launch(instrumentation, "Camera");
        UiDevice device = UiDevice.getInstance(instrumentation);
        return new watcher(device, Res.CAMERA_ACCESS_PERM_WATCHER_PATTERN).checkForCondition();
    }

    /**
     * Check if the the selected policy is checked or not.
     */
    public static boolean checkStatusOfPolicy(UiDevice device, Instrumentation instrumentation,
                                              String switchWidget, String listRes)
            throws Exception {
        UiSelector listViewSelector = new UiSelector().resourceId(listRes);

        new watcher(device, Res.SETTINGS_WATCHER_PATTERN).checkForCondition();
        assertTrue(device.findObject(listViewSelector).exists());

        // Get all the available "Device administrators" options
        int size = device.findObject(listViewSelector).getChildCount();

        // Verify that the correct checkbox (Sample Device Admin) is checked
        for (int i = 0; i < size; i++) {
            UiObject2 sampleDeviceAdminCheckbox = UiAutomatorPlus.findObjectByRelative(
                    instrumentation,
                    By.clazz(switchWidget),
                    By.text("Sample Device Admin"),
                    By.res(listRes));

            if (sampleDeviceAdminCheckbox != null) {
                return sampleDeviceAdminCheckbox.isChecked();
            }
        }
        return false;
    }

    private static UiObject findObjectInScrollable(UiSelector selector) throws UiObjectNotFoundException {
        UiScrollable scrollable = new UiScrollable(new UiSelector().scrollable(true));
        scrollable.scrollIntoView(selector);
        return scrollable.getChild(selector);
    }

    /**
     * Version 1 for api <= 23
     *
     * @param instrumentation Instrumentation
     * @param device          UiDevice
     * @throws Exception
     */
    public static void enableSampleDeviceAdmin_v1(Instrumentation instrumentation, final UiDevice device) throws Exception {
        boolean isAPIDemoInstalled = PackageInstallationUtil.isPackageInstalled(instrumentation,
                "com.example.android.apis");

        if (isAPIDemoInstalled) {
            AppLauncher.launch(instrumentation, "Settings");

            findObjectInScrollable(new UiSelector().textContains("Security")).click();
            findObjectInScrollable(new UiSelector().text("Device administrators")).click();

            device.findObject(new UiSelector().text("Sample Device Admin")).click();

            try {
                device.findObject(new UiSelector().textMatches("(?i)activate(?-i)")).click();
            } catch (UiObjectNotFoundException e) {
                assertTrue("Could not find device administration buttons.",
                        new Wait().until(() -> device.findObject(new UiSelector().text("Cancel")).exists())
                );
                device.findObject(new UiSelector().text("Cancel")).click();
            }
            device.pressHome();
        } else {
            Log.w(TAG, "enableSampleDeviceAdmin: required APK is missing");
        }
    }

    /**
     * Version 2 for api >= 24
     *
     * @param instrumentation Instrumentation
     * @param device          UiDevice
     * @throws Exception
     */
    public static void enableSampleDeviceAdmin_v2(Instrumentation instrumentation, final UiDevice device, String... location) throws Exception {
        boolean isAPIDemoInstalled = PackageInstallationUtil.isPackageInstalled(instrumentation,
                "com.example.android.apis");

        if (isAPIDemoInstalled) {
            AppLauncher.launch(instrumentation, "Settings");
            String securityLabel = location != null && location[0] != null ? location[0] : "Security";

            findObjectInScrollable(new UiSelector().textContains(securityLabel)).click();
            findObjectInScrollable(new UiSelector().textContains("Device admin").
                    resourceId(Res.ANDROID_TITLE_RES)).click();

            device.findObject(new UiSelector().text("Sample Device Admin")).click();

            try {
                findObjectInScrollable(new UiSelector().textContains("Activate")).click();
            } catch (UiObjectNotFoundException e) {
                assertTrue("Could not find device administration buttons.",
                        new Wait().until(() -> device.findObject(new UiSelector().text("Cancel")).exists())
                );
                device.findObject(new UiSelector().text("Cancel")).click();
            }
            device.pressHome();
        } else {
            Log.w(TAG, "enableSampleDeviceAdmin: required APK is missing");
        }
    }

    // Open Downloads folder.
    private static void openDownloads(Instrumentation instrumentation) throws UiObjectNotFoundException {
        UiDevice device = UiDevice.getInstance(instrumentation);
        UiObject downloadsFolder = device.findObject(new UiSelector().text("Download").index(1));
        if (downloadsFolder.waitForExists(5L)) {
            downloadsFolder.clickAndWaitForNewWindow();
        }
    }

    // Check if test file is stored in Downloads folder.
    public static boolean hasTestFile(Instrumentation instrumentation, String testFileName) throws UiObjectNotFoundException {
        UiDevice device = UiDevice.getInstance(instrumentation);
        openDownloads(instrumentation);
        UiObject testFile = device.findObject(new UiSelector().text(testFileName));
        boolean hasTestFile = testFile.waitForExists(5L);
        device.pressBack();
        return hasTestFile;
    }

    // Test file deletion for API 26.
    public static void deleteTestFile_v1(Instrumentation instrumentation, String testFileName) throws UiObjectNotFoundException {
        deleteTestFile(instrumentation, testFileName,
                UiDevice.getInstance(instrumentation).findObject(new UiSelector().resourceId(Res.MENU_LIST_RES)));
    }

    // Test file deletion for APIs 27 and above.
    public static void deleteTestFile_v2(Instrumentation instrumentation, String testFileName, String trashRes) throws UiObjectNotFoundException {
        deleteTestFile(instrumentation, testFileName,
                UiDevice.getInstance(instrumentation).findObject(new UiSelector().resourceIdMatches(trashRes)));
    }

    // Delete test file from Downloads folder.
    private static void deleteTestFile(Instrumentation instrumentation, String testFileName, UiObject trashCan)
            throws UiObjectNotFoundException {
        UiDevice device = UiDevice.getInstance(instrumentation);
        openDownloads(instrumentation);
        UiObject testFile = device.findObject(new UiSelector().text(testFileName));
        if (testFile.waitForExists(5L)) {
            testFile.dragTo(testFile, 100);
        }

        if (trashCan.waitForExists(5L)) {
            trashCan.clickAndWaitForNewWindow();
        }

        UiObject okButton = device.findObject(new UiSelector().textMatches("(?i)ok(?-i)"));
        if (okButton.waitForExists(5L)) {
            okButton.clickAndWaitForNewWindow();
        }
        device.pressBack();
    }

    // Copy test file to Downloads folder, for APIs 26+.
    public static void copyTestFile(Instrumentation instrumentation, String testFileName) throws java.io.IOException {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            Context context = instrumentation.getTargetContext();
            AssetManager assetManager = context.getAssets();
            InputStream in = assetManager.open(testFileName);
            File testFile = new File(Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS), testFileName);
            OutputStream out;
            out = Files.newOutputStream(testFile.toPath());
            byte[] buffer = new byte[1024];
            int read;
            while ((read = in.read(buffer)) != -1) {
                out.write(buffer, 0, read);
            }
            in.close();
            out.close();
        }
    }

    /**
     * Report the current Google login status, using the given account name
     *
     * @param instrumentation UiInstrumentation
     * @param userLoginInfo UiObject
     * @return boolean
     */
    public static boolean verifyGoogleAccountStatus(
            Instrumentation instrumentation, UiObject userLoginInfo) throws Exception {

        UiDevice device = UiDevice.getInstance(instrumentation);

        AppLauncher.launchPath(
                instrumentation, true, "Settings", "Google");

        final UiObject googleAccountLogo = device.findObject(
                new UiSelector()
                        .className("android.widget.ImageView")
                        .resourceId("com.google.android.gms:id/logo"));

        boolean googleAccountLogoExists = new Wait(20000L).until(userLoginInfo::exists);
        if (googleAccountLogoExists){
            googleAccountLogo.waitUntilGone(30000L);
        }
        return new Wait(30000L).until(userLoginInfo::exists);
    };

    /**
     * Remove the given Google account registration from the device
     *
     * @param device UiDevice
     * @param accountName String
     * @return boolean
     */
    public static boolean removeGoogleAccount(
            UiDevice device, String accountName) throws Exception {

        UiObject manageAccount = device.findObject(new UiSelector().
                resourceId(Res.GOOGLE_SERVICES_ACCOUNTS_CHIP_RES));
        if (manageAccount.waitForExists(10000L)) {
            manageAccount.click();
            manageAccount.waitUntilGone(10000L);
        } else {
            return false;
        }

        UiObject userAccount = device.findObject(new UiSelector().
                text(accountName).
                resourceId(Res.ANDROID_TITLE_RES));
        if (userAccount.waitForExists(5000L)) {
            userAccount.click();
            userAccount.waitUntilGone(10000L);
        } else {
            return false;
        }

        UiObject removeAccount = device.findObject(new UiSelector().
                text("Remove account").
                resourceIdMatches(Res.ANDROID_BUTTON + "|" + Res.ANDROID_BUTTON_ONE).
                className(Button.class));
        if (removeAccount.waitForExists(5000L)) {
            removeAccount.click();
            removeAccount.waitUntilGone(10000L);
        } else {
            return false;
        }

        UiObject confirmRemove = device.findObject(new UiSelector().
                text("Remove account").
                resourceId(Res.ANDROID_BUTTON_ONE).
                className(Button.class));
        if (confirmRemove.waitForExists(5000L)) {
            confirmRemove.click();
            confirmRemove.waitUntilGone(10000L);
        } else {
            return false;
        }
        return true;
    }

    /**
     * Navigates to a specified path in the Settings app.
     *
     * This method launches the Settings app and then navigates to a specified path by clicking on the options
     * in the order they are provided. The navigation is performed by scrolling through either the
     * 'main_content_scrollable_container' or the 'content_frame' depending on the pass of the loop.
     *
     * @param device The UiDevice instance that represents an emulator or a connected device.
     * @param path An array of Strings where each String is the name of an option in the Settings app.
     * @return true if the method was able to find and click on all the options in the path array, false otherwise.
     * @throws UiObjectNotFoundException if an option in the path array is not found.
     */
    public static boolean navigateToSettingsPath(UiDevice device, String... path) throws UiObjectNotFoundException {
        Log.i(TAG, "navigateToSettingsPath: Starting method on line " + Thread.currentThread().getStackTrace()[2].getLineNumber());
        device.pressHome();

        try {
            Log.i(TAG, "navigateToSettingsPath: Executing shell command on line " + Thread.currentThread().getStackTrace()[2].getLineNumber());
            device.executeShellCommand("am start -a android.settings.SETTINGS");
        } catch (IOException e) {
            Log.e(TAG, "Error at " + Thread.currentThread().getStackTrace()[2].getFileName() + ":" + Thread.currentThread().getStackTrace()[2].getLineNumber(), e);
            return false;
        }

        for (int i = 0; i < path.length; i++) {
            try {
                String location = path[i];
                Log.i(TAG, "navigateToSettingsPath: Navigating to " + location + " on line " + Thread.currentThread().getStackTrace()[2].getLineNumber());
                UiScrollable scrollableContainer = i == 0 ?
                        new UiScrollable(new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)) :
                        new UiScrollable(new UiSelector().resourceIdMatches(Res.CONTENT_FRAME_CONTAINER_RES));
                if (!new Wait(20000).until(scrollableContainer::exists)) {
                    Log.w(TAG, "navigateToSettingsPath: Scrollable view not found on line " + Thread.currentThread().getStackTrace()[2].getLineNumber());
                    return false;
                }
                UiSelector optionSelector = new UiSelector().text(location);
                UiObject option = device.findObject(optionSelector);

                Log.i(TAG, "navigateToSettingsPath: Dismissing unresponsive popup on line " + Thread.currentThread().getStackTrace()[2].getLineNumber());
                dismissUnresponsivePopup(device);

                if (!new Wait().until(option::exists)) {
                    boolean scrolled = scrollableContainer.scrollIntoView(optionSelector);
                    if (!scrolled) {
                        Log.w(TAG, "navigateToSettingsPath: Failed to navigate to " + location + " on line " + Thread.currentThread().getStackTrace()[2].getLineNumber());
                        return false;
                    }
                }

                if (!new Wait().until(() -> {
                    try {
                        Log.i(TAG, "navigateToSettingsPath: Clicking and waiting for new window on line " + Thread.currentThread().getStackTrace()[2].getLineNumber());
                        return option.clickAndWaitForNewWindow(30000L);
                    } catch (UiObjectNotFoundException e) {
                        Log.e(TAG, "Error at " + Thread.currentThread().getStackTrace()[2].getFileName() + ":" + Thread.currentThread().getStackTrace()[2].getLineNumber(), e);
                        return false;
                    }
                })) {
                    Log.w(TAG, "navigateToSettingsPath: Failed to click on " + location + " on line " + Thread.currentThread().getStackTrace()[2].getLineNumber());
                    return false;
                }
            } catch (Exception e) {
                Log.e(TAG, "Error at " + Thread.currentThread().getStackTrace()[2].getFileName() + ":" + Thread.currentThread().getStackTrace()[2].getLineNumber(), e);
                return false;
            }
        }

        Log.i(TAG, "navigateToSettingsPath: Ending method on line " + Thread.currentThread().getStackTrace()[2].getLineNumber());
        return true;
    }

    /**
     * This method is used to click on a switch in the Settings app and confirm that the switch has been clicked.
     * It first checks if the previous switches (if any) exist and then clicks on the target switch.
     * If any of the previous switches or the target switch do not exist, it logs a warning and returns false.
     * If all switches exist and the target switch is clicked successfully, it returns true.
     *
     * @param device The UiDevice instance that represents an emulator or a connected device.
     * @param switchLabel The label of the switch that this method will click on.
     * @param previousSwitchLabels The labels of the switches that this method will check for existence before clicking on the target switch.
     * @return true if all switches exist and the target switch is clicked successfully, false otherwise.
     */
    public static boolean clickAndConfirmSwitch(UiDevice device, String switchLabel, String... previousSwitchLabels) {
        try {
            dismissUnresponsivePopup(device);

            for (String previousSwitchLabel : previousSwitchLabels) {
                UiObject previousSwitchObject = device.findObject(new UiSelector().text(previousSwitchLabel));
                if (!previousSwitchObject.waitForExists(10000L)) {
                    Log.w(TAG, "Failed to find previous switch object" + previousSwitchLabel);
                    return false;
                }
            }

            UiObject switchObject = device.findObject(new UiSelector().text(switchLabel));
            if (switchObject.waitForExists(10000L)) {
                switchObject.clickAndWaitForNewWindow(10000L);
            }

            return true;
        } catch (UiObjectNotFoundException e) {
            Log.w(TAG, "Failed to find switch object" + switchLabel, e);
            return false;
        }
    }

    /**
     * This method is used to dismiss any unresponsive popup that might appear during the execution of the tests.
     * It first tries to find the unresponsive popup by its resource id. If the popup exists, it clicks on it to dismiss it.
     *
     * @param device The UiDevice instance that represents an emulator or a connected device.
     * @throws UiObjectNotFoundException if the unresponsive popup is not found.
     */
    public static void dismissUnresponsivePopup(UiDevice device) throws UiObjectNotFoundException {
        UiObject notRespondingError = device.findObject(
                new UiSelector().resourceId(Res.ANDROID_ERROR_WAIT_RES));
        if (notRespondingError.waitForExists(5000L)) {
            notRespondingError.click();
            notRespondingError.waitUntilGone(5000L);
        }
    }


    /**
     * Enables the Developer Options in the Android settings.
     *
     * This method navigates to the Developer Options in the Android settings and enables it.
     * If the Developer Options is not initially found, it tries to navigate to "About emulated device" or "About phone"
     * and enables the Developer Options from there.
     *
     * @param instrumentation The instrumentation instance used to interact with the UI.
     * @return true if the Developer Options was successfully enabled, false otherwise.
     * @throws Exception if an error occurs during the process.
     */
    public static boolean enableDeveloperOptions(Instrumentation instrumentation) throws Exception {
        UiDevice device = UiDevice.getInstance(instrumentation);
        boolean result;

        if (navigateToSettingsPath(device, "System", "Developer options")) {
            result = true;
        } else {
            if (navigateToSettingsPath(device, "About emulated device") ||
                    navigateToSettingsPath(device, "About phone")) {
                DeveloperOptionsManager.enableOptions(instrumentation, new DeveloperOptionsManager.SwipeNavigationStrategy(), false);
                result = navigateToSettingsPath(device, "System", "Developer options");
            } else {
                result = false;
            }
        }

        dismissUnresponsivePopup(device);
        return result;
    }
}
