"""This script is to run adb to uninstall apps."""

import subprocess
import sys
import time

sys.path.append("..")

from utils import util
from emu_test.utils import path_utils

test_apk_package = '%s.test' % util.MAIN_APK_PACKAGE

num_trials = 1
while True:
  if num_trials is util.ADB_NUM_MAX_TRIALS:
    sys.exit(-1)
  try:
    adb_binary = path_utils.get_adb_binary()
    print ('Run adb shell to uninstall apps, trial num: %s' % str(num_trials))
    print ('Run adb uninstall %s' % test_apk_package)
    subprocess.call([adb_binary, 'uninstall', test_apk_package])
    print ('Run adb uninstall %s' % util.MAIN_APK_PACKAGE)
    subprocess.call([adb_binary, 'uninstall', util.MAIN_APK_PACKAGE])
    break
  except subprocess.CalledProcessError as err:
    print 'Subprocess call error: {0}'.format(err)
    time.sleep(util.ADB_TRIAL_WAIT_TIME_S)
    num_trials += 1
