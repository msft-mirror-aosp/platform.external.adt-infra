# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe for adb stress testing."""

import os

DEPS = [
  'file',
  'path',
  'platform',
  'properties',
  'python',
  'step',
]

MASTER_USER = 'user'
MASTER_IP = '172.27.213.40'

def RunSteps(api):
  build_dir = api.path['build']
  adb_test_dir = api.path.join(build_dir, os.pardir, 'adb_stress_tests')
  buildername = api.properties['buildername']
  buildnum = api.properties['buildnumber']
  log_dir = 'adb_stress_logs-build_%s' % buildnum

  if api.platform.is_linux:
    android_sdk_home = api.path.join(os.path.expanduser('~'), 'Android', 'android-sdk-linux_public')
  elif api.platform.is_mac:
    android_sdk_home = api.path.join(os.path.expanduser('~'), 'Android', 'android-sdk-macosx_public')
  elif api.platform.is_win:
    android_sdk_home = api.path.join(os.path.expanduser('~'), 'Android', 'android-sdk_public')
  platform_tools_dir = api.path.join(android_sdk_home, 'platform-tools')
  env_path = ['%(PATH)s', platform_tools_dir]
  env = {'PATH': api.path.pathsep.join(env_path)}

  # Run adb stree tests
  with api.step.defer_results():
    for test in ['adb_push_pull_stress.py', 'adb_reboot_stress.py', 'adb_sleep_wake_stress.py']:
      test_path = api.path.join(adb_test_dir, test)
      deferred_step_result = api.python('Run %s' % test, test_path,
                                        ['--duration', '1',
                                         '--count', '1',
                                         '--progress',
                                         '--log-dir', log_dir],
                                        env=env)
      if not deferred_step_result.is_ok: # pragma: no cover
        stderr_output = deferred_step_result.get_error().result.stderr
        print stderr_output

    # Upload logs to GCS (gs://adb_test_traces/)
    script_root = api.path.join(build_dir, os.pardir, 'emu_test')
    log_util_path = api.path.join(script_root, 'utils', 'zip_upload_logs.py')
    logs_dir = '/home/user/buildbot/external/adt-infra/build/masters/master.client.adt/slave_logs/'
    upload_log_args = ['--dir', log_dir,
                       '--name', 'build_%s.zip' % buildnum,
                       '--ip', MASTER_IP,
                       '--user', MASTER_USER,
                       '--dst', '%s%s/' % (logs_dir, buildername),
                       '--build-dir', build_dir,
                       '--skiplog']
    api.python("Zip and Upload Logs", log_util_path, upload_log_args)

def GenTests(api):
  yield (
    api.test('basic') +
    api.platform.name('linux') +
    api.properties(
      mastername='client.adt',
      project='master',
      buildername='Ubuntu 14.04 Intel HD 520',
      buildnumber='12',
    )
  )
  yield (
    api.test('basic') +
    api.platform.name('mac') +
    api.properties(
        mastername='client.adt',
        project='master',
        buildernae='Mac 10.12.1 Intel HD 5000',
        buildnumber='12',
    )
  )
