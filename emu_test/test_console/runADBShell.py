import os
import subprocess


mainAPK_package = "com.android.devtools.server"
launcherClass_name = mainAPK_package + ".Server"
instrumentation_runner = "android.support.test.runner.AndroidJUnitRunner"

TRIAL_WAIT_TIME = 2
NUM_MAX_TRIALS = 5
num_trials = 1

while True:
    if num_trials is NUM_MAX_TRIALS:
        sys.exit(-1)
    try:
        print "Run adb shell instrumentation test command, trial num: " + str(num_trials)
        res_runADBShell = subprocess.call(["adb", "shell", "am", "instrument", "-w", "-e", "class", launcherClass_name, mainAPK_package + ".test/" + instrumentation_runner])
        break
    except subprocess.CalledProcessError as err:
        print("Subprocess call error: {0}".format(err))
        time.sleep(TRIAL_WAIT_TIME)
        num_trials = num_trials + 1
