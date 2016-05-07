package com.android.devtools.systemimage.uitest.utils;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;

/**
 * Utility to invoke shell commands.
 */
public class ShellUtil {
    public static final String TAG = ShellUtil.class.getName();

    /**
     * Shell result class definition.
     */
    public static class ShellResult {
        public final String stdout;
        public final String stderr;

        /**
         * Constructs the class.
         */
        public ShellResult(String stdout, String stderr) {
            this.stdout = stdout;
            this.stderr = stderr;
        }
    }

    /**
     * Invokes shell command.
     * <p>
     * Note shell commands that require system privilege cannot be invoked through the method.
     *
     * @param cmd the command to call in shell
     * @return {@link ShellResult}
     * @throws IOException if File IO fails.
     */
    public static ShellResult invokeCommand(String cmd) throws IOException {
        Process p = Runtime.getRuntime().exec(cmd);
        BufferedReader stdoutReader = new BufferedReader(new InputStreamReader(p.getInputStream()));
        BufferedReader stderrReader = new BufferedReader(new InputStreamReader(p.getErrorStream()));
        String line;
        StringBuilder stdout = new StringBuilder();
        while ((line = stdoutReader.readLine()) != null) {
            stdout.append(line).append("\n");
        }
        stdoutReader.close();
        StringBuilder stderr = new StringBuilder();
        while ((line = stderrReader.readLine()) != null) {
            stdout.append(line).append("\n");
        }
        stderrReader.close();
        if (p != null) {
            p.destroy();
        }
        return new ShellResult(stdout.toString(), stderr.toString());
    }
}
