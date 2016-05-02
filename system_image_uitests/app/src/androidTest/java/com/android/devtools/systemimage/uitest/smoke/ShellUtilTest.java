package com.android.devtools.systemimage.uitest.smoke;

import android.support.test.filters.SdkSuppress;

import com.android.devtools.systemimage.uitest.framework.AbstractSystemImageTestCase;
import com.android.devtools.systemimage.uitest.utils.ShellUtil;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;

/**
 * Test suite on shell utility.
 */
@SdkSuppress(minSdkVersion = 18)
public class ShellUtilTest extends AbstractSystemImageTestCase {

  /**
   * Tests the integrity of Shell utilities.
   * @throws Exception
   */
  public void testShellUtilIntegrity() throws Exception {
    String cmd = "ls /system/bin";
    ShellUtil.ShellResult result = ShellUtil.invokeCommand(cmd);
    // Check if the cmd is executed correctly.
    assertTrue(result.stderr, result.stderr.length() == 0);

    // Verify the integrity of the shell utilities.
    InputStream inputStream = mInstrumentation.getTargetContext().getAssets().open("util.txt");
    BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream, "UTF-8"));
    String line;
    StringBuilder util = new StringBuilder();
    while ((line = reader.readLine()) != null) {
      util.append(line).append("\n");
    }
    assertEquals("Failure: The shell util is incomplete!", util.toString(), result.stdout);
  }
}
