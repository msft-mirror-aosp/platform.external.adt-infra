package com.android.devtools.systemimage.uitest.utils;

import android.app.Instrumentation;
import android.graphics.Rect;
import android.support.test.uiautomator.By;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObject2;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;
import android.util.Log;
import android.widget.Switch;

import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.watchers.CameraAccessPermissionsWatcher;
import com.android.devtools.systemimage.uitest.watchers.SettingsTestPopupWatcher;

import junit.framework.Assert;

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
        if (!itemList.exists()) {
            itemList = new UiScrollable(new UiSelector().resourceIdMatches(
                    Res.LAUNCHER_LIST_CONTAINER_RES));
        }
        return itemList.setAsVerticalList();
    }

    /**
     * Launches Settings and find the item with the given name. Returns the item.
     */
    public static UiObject findItem(Instrumentation instrumentation, String name) throws Exception {
        UiScrollable itemList = launchAndGetItemList(instrumentation);
        UiObject item = itemList.getChildByText(
                new UiSelector().className("android.widget.TextView"), name);
        if (item.waitForExists(TimeUnit.SECONDS.toMillis(5))) {
            return item;
        } else {
            throw new UiObjectNotFoundException("Failed to find the item in Settings.");
        }
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

        Assert.assertTrue(actionButton.getText().toLowerCase().contains(change.toLowerCase()));

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
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param appType String describing the application type, as listed on the App permissions
     *                screen.
     * @throws Exception if it fails to find a UI object.
     */
    public static UiObject getAppPermissions(
            Instrumentation instrumentation, String appType, String appText)
            throws Exception {

        UiDevice device = UiDevice.getInstance(instrumentation);

        SettingsUtil.openItem(instrumentation, appText);

        UiObject appPermissionsLabel = device.findObject(new UiSelector().text("App permissions"));
        boolean hasAppPermissionsLabel = appPermissionsLabel.waitForExists(5L);
        if (hasAppPermissionsLabel) {
            appPermissionsLabel.clickAndWaitForNewWindow();
        }
        UiScrollable appPermissionsList = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_CONTENT_RES));
        if (appPermissionsList.waitForExists(TimeUnit.SECONDS.toMillis(5))) {
            return appPermissionsList.getChildByText(new UiSelector().className("android.widget.TextView"), appType);
        } else {
            throw new UiObjectNotFoundException("Failed to find the item in App permissions.");
        }
    }

    /**
     * Enable or disable permissions settings for a given application type
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
    public static void setAppPermissions(
            Instrumentation instrumentation, String appType,
            String appName, boolean enablePermissions,
            String denyButtonText, String appText)
            throws Exception {

        UiDevice device = UiDevice.getInstance(instrumentation);

        getAppPermissions(instrumentation, appType, appText);

        device.findObject(new UiSelector().text(appType)).click();

        UiScrollable locationPermissions = new UiScrollable(new UiSelector().resourceId(Res.ANDROID_CONTENT_RES));
        locationPermissions.getChildByText(new UiSelector().className("android.widget.TextView"), appName);

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

    public static void clickAdvancedMenu(UiDevice device) throws Exception {
        final UiObject advancedMenu = device.findObject(new UiSelector().text("Advanced"));
        boolean hasAdvancedMenu = new Wait().until(new Wait.ExpectedCondition() {
            @Override
            public boolean isTrue() {
                return advancedMenu.exists();
            }
        });

        if (hasAdvancedMenu) {
            advancedMenu.click();
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
        new CameraAccessPermissionsWatcher(device).checkForCondition();
    }

    public static boolean verifyCameraAppDisabled(UiDevice device) {
        return device.hasObject(By.textContains(
                "Camera has been disabled because of security policies")) ||
                device.hasObject(By.text("Can't connect to the camera."));
    }

    /**
     * Check if the the selected policy is checked or not.
     */
    public static boolean checkStatusOfPolicy(UiDevice device, Instrumentation instrumentation, String switchWidget)
            throws Exception {
        UiSelector listViewSelector = new UiSelector().resourceId(Res.ANDROID_LIST_RES);

        new SettingsTestPopupWatcher(device).checkForCondition();
        assertTrue(device.findObject(listViewSelector).exists());

        // Get all the available "Device administrators" options
        int size = device.findObject(listViewSelector).getChildCount();

        // Verify that the correct checkbox (Sample Device Admin) is checked
        for (int i = 0; i < size; i++) {
            UiObject2 sampleDeviceAdminCheckbox = UiAutomatorPlus.findObjectByRelative(
                    instrumentation,
                    By.clazz(switchWidget),
                    By.text("Sample Device Admin"),
                    By.res(Res.ANDROID_LIST_RES));

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
}