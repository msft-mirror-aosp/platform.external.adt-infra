package com.android.devtools.systemimage.uitest.unittest.utils;

import android.support.test.filters.SdkSuppress;

import com.android.devtools.systemimage.uitest.framework.AbstractSystemImageTestCase;
import com.android.devtools.systemimage.uitest.utils.AppLauncher;
import com.android.devtools.systemimage.uitest.utils.TaskManager;

/**
 * Unit test on {@link TaskManager}.
 */
@SdkSuppress(minSdkVersion = 18)
public class TaskManagerTest extends AbstractSystemImageTestCase {

    public void testTaskManager() throws Exception {
        AppLauncher.launch(mInstrumentation, "Email");
        TaskManager.killApp(mInstrumentation, "Email");

        AppLauncher.launch(mInstrumentation, "API Demos");
        TaskManager.killApp(mInstrumentation, "API Demos");
    }
}
