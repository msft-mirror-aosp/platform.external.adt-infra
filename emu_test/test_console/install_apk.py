"""This script is to install apk."""

import os
import subprocess
import sys
import time
import platform

from utils import util

install_apk_script_dir = os.path.dirname(os.path.realpath(__file__))
apk_dir = os.path.join(install_apk_script_dir, 'utils', 'apks')

num_trials = 1
while True:
  if num_trials is util.ADB_NUM_MAX_TRIALS:
    sys.exit(-1)
  try:
    adb_binary = os.path.join(os.environ['ANDROID_SDK_ROOT'], 'platform-tools', 'adb')
    print 'Run APK install command, trial num: %s' % str(num_trials)
    appDebug = os.path.join(apk_dir,
                            'app-debug-'+platform.system()+'.apk')
    appDebugAndroidTest = os.path.join(apk_dir,
                                       'app-debug-androidTest-'+platform.system()+'.apk')
    subprocess.call([adb_binary, 'install', '-r', appDebug])
    subprocess.call([adb_binary, 'install', '-r', appDebugAndroidTest])
    break
  except subprocess.CalledProcessError as err:
    print 'Subprocess call error: {0}'.format(err)
    time.sleep(util.ADB_TRIAL_WAIT_TIME_S)
    num_trials += 1
