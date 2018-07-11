package com.android.devtools.systemimage.uitest.utils.api25;
import android.app.Instrumentation;
import android.graphics.Rect;
import android.support.test.uiautomator.By;
import android.support.test.uiautomator.UiDevice;
import android.support.test.uiautomator.UiObject;
import android.support.test.uiautomator.UiObject2;
import android.support.test.uiautomator.UiObjectNotFoundException;
import android.support.test.uiautomator.UiScrollable;
import android.support.test.uiautomator.UiSelector;

import com.android.devtools.systemimage.uitest.common.Res;
import com.android.devtools.systemimage.uitest.watchers.SettingsTestPopupWatcher;

import junit.framework.Assert;

import java.util.concurrent.TimeUnit;

import static junit.framework.Assert.assertTrue;

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
     * Launches Settings and scroll to the item whose name contains the given text.
     */
    public static boolean scrollToItem(
            Instrumentation instrumentation, String text) throws Exception {
        UiScrollable itemList = launchAndGetItemList(instrumentation);
        return itemList.scrollIntoView(new UiSelector().textContains(text));
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
    public static void activate(Instrumentation instrumentation, String adminName)
            throws Exception {
        changePolicyActivation(instrumentation, adminName, "Activate");
    }

    /**
     * Deactivate "Sample Device Admin" policy under Device administrators.
     *
     * @param instrumentation see {@link android.test.InstrumentationTestCase#getInstrumentation()
     *                        getInstrumentation}
     * @param adminName admin policy name
     * @throws Exception if it fails to find a UI widget.
     */
    public static void deactivate(Instrumentation instrumentation, String adminName)
            throws Exception {
        changePolicyActivation(instrumentation, adminName, "Deactivate");
    }

    public static void launchDeviceAdminApps(Instrumentation instrumentation) throws Exception {
        SettingsUtil.openItem(instrumentation, "Security");

        UiScrollable itemList =
                new UiScrollable(
                        new UiSelector().resourceIdMatches(Res.SETTINGS_LIST_CONTAINER_RES)
                );
        itemList.setAsVerticalList();
        // Go to device administrators page.
        itemList.getChildByText(new UiSelector().className("android.widget.TextView"),
                "Device administrators").clickAndWaitForNewWindow();
    }

    private static void changePolicyActivation(
            Instrumentation instrumentation, String adminName, String change) throws Exception {

        UiDevice device = UiDevice.getInstance(instrumentation);
        launchDeviceAdminApps(instrumentation);

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

        assertTrue(actionButton.getText().toLowerCase().contains(change.toLowerCase()));

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
            Instrumentation instrumentation, String appType)
            throws Exception {

        UiDevice device = UiDevice.getInstance(instrumentation);
        SettingsUtil.openItem(instrumentation, "Apps");

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
            String appName, boolean enablePermissions)
            throws Exception {

        UiDevice device = UiDevice.getInstance(instrumentation);

        getAppPermissions(instrumentation, appType);

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

            final UiObject denyButton = device.findObject(new UiSelector().text("DENY ANYWAY"));
            try {
                boolean dialogLaunched =
                        new Wait().until(new Wait.ExpectedCondition() {
                            @Override
                            public boolean isTrue() {return denyButton.exists();
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
     * Check if the the selected policy is checked or not.
     */
    public static boolean checkStatusOfPolicy(Instrumentation instrumentation, UiDevice device)
            throws Exception {
        UiSelector listViewSelector = new UiSelector().resourceId(Res.ANDROID_LIST_RES);

        new SettingsTestPopupWatcher(device).checkForCondition();
        assertTrue(device.findObject(listViewSelector).exists());

        // Get all the available "Device administrators" options
        int size = device.findObject(listViewSelector).getChildCount();

        // Verify that the correct checkbox (Sample Device Admin) is checked
        for (int i = 0; i < size; i++) {
            UiSelector sampleDeviceSelection = listViewSelector.childSelector(new
                    UiSelector().index(i));

            String switchWidget = "android.widget.CheckBox";

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
}