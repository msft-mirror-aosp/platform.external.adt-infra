package com.android.devtools.systemimage.uitest.utils;

import android.app.Instrumentation;
import android.content.Context;
import android.content.res.AssetManager;
import android.graphics.Rect;
import android.os.Environment;
import android.support.test.uiautomator.By;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObject2;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;
import android.util.Log;
import android.widget.LinearLayout;
import android.widget.Switch;

import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.watchers.watcher;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.concurrent.TimeUnit;

import static org.junit.Assert.assertTrue;

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
    public static UiObject findItem(Instrumentation instrumentation, String name) throws Exception {
        UiScrollable itemList = launchAndGetItemList(instrumentation);
        UiObject item = itemList.getChildByText(
                new UiSelector().className("android.widget.TextView"), name);

        assertTrue("Failed to find the item in Settings list.",
                item.waitForExists(TimeUnit.SECONDS.toMillis(5)));

        return item;
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
     * @param adminName admin policy name
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
     * @param adminName admin policy name
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
                new UiSelector().resourceId("com.android.settings:id/action_button"));

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
     * For API <= 25
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param appType String describing the application type, as listed on the App permissions
     *                screen.
     * @throws Exception if it fails to find a UI object.
     */
    public static boolean getAppPermissions_v1(
            Instrumentation instrumentation, String appType, String appText)
            throws Exception {

        UiDevice device = UiDevice.getInstance(instrumentation);

        SettingsUtil.openItem(instrumentation, appText);

        UiScrollable appPermissionsList = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_CONTENT_RES));
        if (appPermissionsList.waitForExists(TimeUnit.SECONDS.toMillis(20))) {
            appPermissionsList.getChildByText(new UiSelector().className("android.widget.TextView"), appType).clickAndWaitForNewWindow();
        } else {
            throw new UiObjectNotFoundException("Failed to find the item in Apps.");
        }

        UiObject appPermissionsLabel = device.findObject(new UiSelector().text("Permissions"));
        boolean hasAppPermissionsLabel = appPermissionsLabel.waitForExists(5L);
        if (hasAppPermissionsLabel) {
            appPermissionsLabel.clickAndWaitForNewWindow();
        }

        return hasAppPermissionsLabel;
    }

    /**
     * Fetch permissions settings for a given application type.
     * For API >= 26
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param appType String describing the application type, as listed on the App permissions
     *                screen.
     * @throws Exception if it fails to find a UI object.
     */
    public static UiObject getAppPermissions_v2(
            Instrumentation instrumentation, String appType, String appText, String permissionText)
            throws Exception {

        UiDevice device = UiDevice.getInstance(instrumentation);

        SettingsUtil.openItem(instrumentation, appText);

        SettingsUtil.clickAdvancedMenu(device);
        UiObject appPermissionsLabel = device.findObject(new UiSelector().text(permissionText));
        boolean hasAppPermissionsLabel = appPermissionsLabel.waitForExists(5L);
        if (hasAppPermissionsLabel) {
            appPermissionsLabel.clickAndWaitForNewWindow();
        }
        UiScrollable appPermissionsList = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_CONTENT_RES));
        if (appPermissionsList.waitForExists(TimeUnit.SECONDS.toMillis(60L))) {
            appPermissionsList.setAsVerticalList();
            UiSelector appSelector = new UiSelector().text(appType);
            if (appPermissionsList.scrollIntoView(appSelector)) {
                return device.findObject(appSelector);
            }
        }

        throw new UiObjectNotFoundException("Failed to find the item in App permissions.");
    }

    /**
     * Enable or disable permissions settings for a given application type
     * For API <= 25
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param appType String describing the application type, as listed on the App permissions
     *                screen.
     * @param appName String describing the application name, as listed on the {appType}
     *                permissions screen.
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

        getAppPermissions_v1(instrumentation, appName, appText);

        UiObject2 permissionsBtn = UiAutomatorPlus.findObjectByRelative(
                instrumentation,
                By.clazz("android.widget.Switch"),
                By.text(appType),
                By.clazz("android.widget.LinearLayout"),
                2);

        if (!permissionsBtn.isChecked() && enablePermissions)
            permissionsBtn.click();

        else if ((permissionsBtn.isChecked() && !enablePermissions)) {
            permissionsBtn.click();

            final UiObject denyButton = device.findObject(new UiSelector().text(denyButtonText));

            try {
                boolean dialogLaunched =
                        new Wait().until(new Wait.ExpectedCondition() {
                            @Override
                            public boolean isTrue() throws UiObjectNotFoundException {return denyButton.exists();
                            }
                        });
                if (dialogLaunched)
                    denyButton.click();
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    /**
     * Enable or disable permissions settings for a given application type
     * For API >= 26
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param appType String describing the application type, as listed on the App permissions
     *                screen.
     * @param appName String describing the application name, as listed on the {appType}
     *                permissions screen.
     * @param enablePermissions boolean indicating whether the permissions should be enabled
     *                          or disabled.
     * @throws Exception if it fails to find a UI object.
     */
    public static void setAppPermissions_v2(
            Instrumentation instrumentation, String appType,
            String appName, boolean enablePermissions,
            String denyButtonText, String appText,
            String permissionText)
            throws Exception {

        UiDevice device = UiDevice.getInstance(instrumentation);

        getAppPermissions_v2(instrumentation, appType, appText, permissionText);

        device.findObject(new UiSelector().text(appType)).click();

        UiScrollable locationPermissions = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_CONTENT_RES));
        locationPermissions.getChildByText(new UiSelector().className("android.widget.TextView"), appName);

        UiScrollable permissionList = new UiScrollable(new UiSelector().resourceIdMatches(Res.ANDROID_LIST_RES));

        UiObject permissionsBtn =
                SettingsUtil.findObjectByRelative(permissionList,appName, LinearLayout.class.getName());

        if (!permissionsBtn.isChecked() && enablePermissions)
            permissionsBtn.click();

        else if ((permissionsBtn.isChecked() && !enablePermissions)) {
            permissionsBtn.click();

            final UiObject denyButton = device.findObject(new UiSelector().text(denyButtonText));

            try {
                boolean dialogLaunched =
                        new Wait().until(new Wait.ExpectedCondition() {
                            @Override
                            public boolean isTrue() throws UiObjectNotFoundException {return denyButton.exists();
                            }
                        });
                if (dialogLaunched)
                    denyButton.click();
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    /**
     * Enable or disable permissions settings for a given application type
     * For API >= 29
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param appType String describing the application type, as listed on the App permissions
     *                screen.
     * @param appName String describing the application name, as listed on the {appType}
     *                permissions screen.
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

        UiDevice device = UiDevice.getInstance(instrumentation);

        getAppPermissions_v2(instrumentation, appType, appText, permissionText);

        device.findObject(new UiSelector().text(appType)).click();

        UiScrollable permissionList = new UiScrollable(new UiSelector().resourceId("com.android.permissioncontroller:id/recycler_view"));
        UiObject appButton = permissionList.getChildByText(new UiSelector().className("android.widget.TextView"), appName);

        if (appButton.exists())
            appButton.click();

        UiObject permissionsAllowBtn = device.findObject(
                new UiSelector().resourceId("com.android.permissioncontroller:id/allow_radio_button"));
        UiObject permissionsDenyBtn = device.findObject(
                new UiSelector().resourceId("com.android.permissioncontroller:id/deny_radio_button"));

        if (enablePermissions)
            permissionsAllowBtn.click();

        else if ((permissionsAllowBtn.isChecked() && !enablePermissions)) {
            permissionsDenyBtn.click();

            final UiObject denyButton = device.findObject(new UiSelector().text(denyButtonText));

            try {
                boolean dialogLaunched =
                        new Wait().until(new Wait.ExpectedCondition() {
                            @Override
                            public boolean isTrue() throws UiObjectNotFoundException {return denyButton.exists();
                            }
                        });
                if (dialogLaunched)
                    denyButton.click();
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    /*
     * Helper function to click "Advanced" is setting menu if it exists.
     * Otherwiese it should do nothing and shopuld not throw any exception.
     */
    public static void clickAdvancedMenu(UiDevice device) {
        UiScrollable itemList =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)
                );
        itemList.setAsVerticalList();
        UiSelector advancedButton = new UiSelector().text("Advanced");

        try {
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
                assertTrue("Could not find Date Time switch", false);
            }
        }
        return null;
    }

    public static UiObject findObjectByRelative(UiScrollable verticalList, String childText, String classType) throws Exception{
        UiObject uiObject = verticalList.getChildByText(new UiSelector().className(classType),childText);
        return uiObject.getChild(new UiSelector().className(Switch.class.getName()));
    }

    public static void setCameraEnabled(final boolean enableCameraDevices, Instrumentation instrumentation, final UiDevice device) throws Exception {
        boolean isAPIDemoInstalled = PackageInstallationUtil.isPackageInstalled(instrumentation,
                "com.example.android.apis");

        if (isAPIDemoInstalled) {
            final boolean enableCameras = enableCameraDevices;
            String cameraCheckboxLabel = enableCameras ? "Device cameras disabled" :
                    "Device cameras enabled";
            final UiObject enableCamerasCheckbox = device.findObject(
                    new UiSelector().text(cameraCheckboxLabel));

            AppLauncher.launch(instrumentation, "API Demos");
            boolean widgetExists = new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws Exception {
                    return device.findObject(new UiSelector().textContains("App")).exists();
                }
            });
            if (widgetExists) {
                device.findObject(new UiSelector().textContains("App")).click();
            }
            widgetExists = new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws Exception {
                    return device.findObject(new UiSelector().text("Device Admin")).exists();
                }
            });

            if (widgetExists) {
                device.findObject(new UiSelector().text("Device Admin")).click();
            }
            widgetExists = new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws Exception {
                    return device.findObject(new UiSelector().text("General")).exists();
                }
            });
            if (widgetExists) {
                device.findObject(new UiSelector().text("General")).click();
            }

            widgetExists = new Wait().until(new Wait.ExpectedCondition() {
                @Override
                public boolean isTrue() throws Exception {
                    return enableCamerasCheckbox.exists();
                }
            });

            if (widgetExists) {
                enableCamerasCheckbox.click();
            }

            device.pressHome();
        } else {
            Log.w(TAG, "setCameraEnabled: required APK is missing");
        }
    }

    public static void gotoCameraApp(Instrumentation instrumentation, UiDevice device) throws Exception {
        AppLauncher.launch(instrumentation, "Camera");
        new watcher(device, Res.CAMERA_ACCESS_PERM_WATCHER_PATTERN).checkForCondition();
    }

    public static boolean verifyCameraAppDisabled(UiDevice device) throws UiObjectNotFoundException {
        boolean errorTextExist = device.hasObject(By.textContains(
                "Camera has been disabled because of security policies")) ||
                device.hasObject(By.text("Can't connect to the camera."));

        if (errorTextExist) {
            device.findObject(new UiSelector().textMatches("(?i)dismiss(?-i)")).click();
        }

        return errorTextExist;
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
                boolean isChecked = sampleDeviceAdminCheckbox.isChecked();
                return isChecked;
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
     * @param instrumentation
     * @param device
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
                        new Wait().until(new Wait.ExpectedCondition() {
                            @Override
                            public boolean isTrue() throws Exception {
                                return device.findObject(new UiSelector().text("Cancel")).exists();
                            }
                        })
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
     * @param instrumentation
     * @param device
     * @throws Exception
     */
    public static void enableSampleDeviceAdmin_v2(Instrumentation instrumentation, final UiDevice device) throws Exception {
        boolean isAPIDemoInstalled = PackageInstallationUtil.isPackageInstalled(instrumentation,
                "com.example.android.apis");

        if (isAPIDemoInstalled) {
            AppLauncher.launch(instrumentation, "Settings");

            findObjectInScrollable(new UiSelector().textContains("Security")).click();
            findObjectInScrollable(new UiSelector().textContains("Device admin").
                    resourceId(Res.ANDROID_TITLE_RES)).click();

            device.findObject(new UiSelector().text("Sample Device Admin")).click();

            try {
                findObjectInScrollable(new UiSelector().textContains("Activate")).click();
            } catch (UiObjectNotFoundException e) {
                assertTrue("Could not find device administration buttons.",
                        new Wait().until(new Wait.ExpectedCondition() {
                            @Override
                            public boolean isTrue() throws Exception {
                                return device.findObject(new UiSelector().text("Cancel")).exists();
                            }
                        })
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
                UiDevice.getInstance(instrumentation).findObject(new UiSelector().resourceId(trashRes)));
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

    // Copy test file to Downloads folder.
    public static void copyTestFile(Instrumentation instrumentation, String testFileName) throws java.io.IOException {
        Context context = instrumentation.getTargetContext();
        AssetManager assetManager = context.getAssets();
        InputStream in = assetManager.open(testFileName);
        File testFile = new File(Environment.getExternalStoragePublicDirectory(
                Environment.DIRECTORY_DOWNLOADS), testFileName);
        OutputStream out = new FileOutputStream(testFile);
        byte[] buffer = new byte[1024];
        int read;
        while ((read = in.read(buffer)) != -1) {
            out.write(buffer, 0, read);
        }
        in.close();
        out.close();
    }
}
