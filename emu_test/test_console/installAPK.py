import os
import subprocess
import sys
import time

installAPK_script_dir = os.path.dirname(os.path.realpath(__file__))
servlet_launcher_dir = os.path.join(installAPK_script_dir, 'Server')
mainAPK_path = os.path.join(servlet_launcher_dir, 'app', 'build', 'outputs', 'apk', 'app-debug.apk')
androidTestAPK_path = os.path.join(servlet_launcher_dir, 'app', 'build', 'outputs', 'apk', 'app-debug-androidTest-unaligned.apk')

gradle = ""
if os.name == 'nt':
    gradle = "gradlew.bat"
else:
    gradle = "./gradlew"

TRIAL_WAIT_TIME = 2
NUM_MAX_TRIALS = 5
num_trials = 1

os.chdir(servlet_launcher_dir)

while True:
    if num_trials is NUM_MAX_TRIALS:
        sys.exit(-1)
    try:
        print "Run APK install command, trial num: " + str(num_trials)
        res_gradlew_buildMain = subprocess.check_call([gradle, "assemble"])
        res_gradlew_buildAndroidTest = subprocess.check_call([gradle, "assembleAndroidTest"])
        res_installMain = subprocess.check_call(["adb", "install", "-r", mainAPK_path])
        res_installAndroidTest = subprocess.check_call(["adb", "install", "-r", androidTestAPK_path])
        break
    except subprocess.CalledProcessError as err:
        print("Subprocess call error: {0}".format(err))
        time.sleep(TRIAL_WAIT_TIME)
        num_trials = num_trials + 1
