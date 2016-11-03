"""This script is to install apk."""

import os
import subprocess
import sys
import time

from utils import util

install_apk_script_dir = os.path.dirname(os.path.realpath(__file__))
servlet_launcher_dir = os.path.join(install_apk_script_dir, 'Server')
main_apk_path = os.path.join(servlet_launcher_dir,
                             'app', 'build', 'outputs', 'apk', 'app-debug.apk')
android_test_apk_path = os.path.join(servlet_launcher_dir,
                                     'app', 'build', 'outputs', 'apk',
                                     'app-debug-androidTest-unaligned.apk')

gradle = ''
if os.name == util.WINDOWS_OS_NAME:
  gradle = 'gradlew.bat'
else:
  gradle = './gradlew'

os.chdir(servlet_launcher_dir)

num_trials = 1
while True:
  if num_trials is util.ADB_NUM_MAX_TRIALS:
    sys.exit(-1)
  try:
    print 'Run APK install command, trial num: %s' % str(num_trials)
    res_gradlew_build_main = subprocess.check_call([gradle, 'assemble'])
    res_gradlew_build_android_test = (subprocess
                                      .check_call([gradle,
                                                   'assembleAndroidTest']))
    res_install_main = subprocess.check_call(['adb', 'install', '-r',
                                              main_apk_path])
    res_install_android_test = subprocess.check_call(['adb', 'install', '-r',
                                                      android_test_apk_path])
    break
  except subprocess.CalledProcessError as err:
    print 'Subprocess call error: {0}'.format(err)
    time.sleep(util.ADB_TRIAL_WAIT_TIME_S)
    num_trials += 1
