"""This script is to run adb shell instrumentation test."""

import subprocess
import sys
import time

from utils import util

main_apk_package = 'com.android.devtools.server'
launcher_class_name = '%s.Server' % main_apk_package
instrumentation_runner = 'android.support.test.runner.AndroidJUnitRunner'

num_trials = 1
while True:
  if num_trials is util.ADB_NUM_MAX_TRIALS:
    sys.exit(-1)
  try:
    print ('Run adb shell instrumentation test command, trial num: %s'
           % str(num_trials))
    res_run_adb_shell = subprocess.call(['adb', 'shell', 'am', 'instrument',
                                         '-w', '-e' 'class',
                                         launcher_class_name,
                                         ('%s.test/%s'
                                          % (main_apk_package,
                                             instrumentation_runner))])
    break
  except subprocess.CalledProcessError as err:
    print 'Subprocess call error: {0}'.format(err)
    time.sleep(util.ADB_TRIAL_WAIT_TIME_S)
    num_trials += 1
