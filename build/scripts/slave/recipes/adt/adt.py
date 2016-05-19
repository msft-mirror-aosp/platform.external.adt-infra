# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe for emulator boot tests."""

from recipe_engine.types import freeze
import os
import csv
import collections

DEPS = [
    'path',
    'platform',
    'properties',
    'python',
    'raw_io',
    'step',
    'json',
    'trigger',
]

MASTER_USER = 'user'
MASTER_IP = '172.27.213.40'

bootStep = collections.namedtuple('bootStep', 'description, filter')
def RunSteps(api):
  buildername = api.properties['buildername']
  project = str(api.properties['project'])
  file_list = api.properties.get('file_list')
  download_path = api.path['slave_build'].join('')
  env_path = ['%(PATH)s']
  emulator_branches = ['emu-master-dev', 'emu-2.0-release']
  is_cts = "cts" in str(api.properties.get('scheduler'))

  # find android sdk root directory
  home_dir = os.path.expanduser('~')
  if api.platform.is_mac:
    android_sdk_home = os.path.join(home_dir, 'Android', 'android-sdk-macosx')
  elif api.platform.is_linux:
    android_sdk_home = os.path.join(home_dir, 'Android', 'android-sdk-linux')
  # On windows, we need cygwin and GnuWin for commands like, rm, scp, unzip
  elif api.platform.is_win:
    android_sdk_home = os.path.join(home_dir, 'Android', 'android-sdk')
    if api.platform.bits == 64:
      gnu_path = 'C:\\Program Files (x86)\\GnuWin32\\bin'
      cygwin_path = 'C:\\cygwin64\\bin'
    else:
      gnu_path = 'C:\\Program Files\\GnuWin32\\bin'
      cygwin_path = 'C:\\cygwin\\bin'
    env_path = [gnu_path, cygwin_path] + env_path
  else:
    raise # pragma: no cover

  is_cross_build = api.properties.get('triggered')
  if project in emulator_branches and not is_cross_build and not is_cts:
    android_sdk_home += "_public"
  else:
    android_sdk_home += "_image-builds"
  sdk_emulator_path = api.path.join(android_sdk_home, 'tools', 'emulator')

  android_tools_dir = os.path.join(android_sdk_home, 'tools')
  android_platform_dir = os.path.join(android_sdk_home, 'platform-tools')
  android_buildtools_dir = os.path.join(android_sdk_home, 'build-tools', '23.0.2')
  env_path += [android_tools_dir, android_platform_dir, android_buildtools_dir]
  env = {'PATH': api.path.pathsep.join(env_path),
         'ANDROID_SDK_ROOT': android_sdk_home}

  # Find emulator script based on build directory
  # Emulator scripts are located [project root]/emu_test
  build_dir = api.path['build']
  script_root = api.path.join(build_dir, os.pardir, 'emu_test')
  dotest_path = api.path.join(script_root, 'dotest.py')
  image_util_path = api.path.join(script_root, 'utils', 'download_unzip_image.py')
  buildnum = api.properties['buildnumber']
  rev = api.properties['revision']
  log_util_path = api.path.join(script_root, 'utils', 'zip_upload_logs.py')
  init_bot_util_path = api.path.join(script_root, 'utils', 'emu_bot_init.py')
  log_dir = 'logs-build_%s-rev_%s' % (buildnum, rev)

  bootSteps = {
               'emu-master-dev': bootStep('public', '{"ori": "public"}'),
               'emu-2.0-release': bootStep('public', '{"ori": "public"}'),
               'mnc-emu-dev': bootStep('MNC', '{"ori": "mnc"}'),
               'lmp-mr1-emu-dev': bootStep('LMP_MR1', '{"ori": "lmp-mr1"}'),
               'nyc-emu-dev': bootStep('NYC', '{"ori": "nyc"}'),
               'nyc-emu-release': bootStep('NYC', '{"ori": "nyc"}'),
               'lmp-emu-dev': bootStep('LMP', '{"ori": "lmp"}'),
               'klp-emu-dev': bootStep('KLP', '{"ori": "klp"}'),
              }

  # figure out which emulator to use, and which test steps to run
  # For case 1, system-image builds, use only public emulator, and run boot test for the changing branch
  # For case 2, emulator builds, use the triggering emulator branch, run public boot test
  # For case 3, cross builds, if triggering factor is emulator branch, then use that emulator branch, on all system image other than public
  # case 4, if changes are in system-image branch, need to check against all of known good emulator branches, and on the triggering branch image

  def getTestConfig(project, cross_build):
    # case 1
    if project not in emulator_branches and not cross_build:
      emulator_branch_to_use = [android_sdk_home]
      steps_to_run = [project]
    # case 2
    elif project in emulator_branches and not cross_build:
      emulator_branch_to_use = [project]
      steps_to_run = [project]
    # case 3
    elif project in emulator_branches and cross_build:
      emulator_branch_to_use = [project]
      steps_to_run = [x for x in bootSteps if x not in emulator_branches]
    # case 4
    else:
      emulator_branch_to_use = [x for x in emulator_branches]
      steps_to_run = [project]
    return emulator_branch_to_use, steps_to_run

  # Functions to save and retrieve properties
  # We save the last known good revision in a local csv file, then read it
  # for cross build
  # Since green build only triggers cross build on itself, local file works fine
  # csv file format: branch,revison,file_list
  build_cache = api.path.join(script_root, 'config', 'build_cache.csv')
  def getProps():
    props = {'blamelist': api.properties.get('blamelist'),
             'file_list': file_list,
             'logs_dir': api.properties.get('logs_dir'),
             'buildername': '%s_cross-builds' % buildername.rsplit('_',1)[0],
             'triggered': 'True',
             'got_revision': rev,
             project: rev,
             'revision': rev}
    last_build = {}
    with open(build_cache,'r') as csvfile:
      filereader = csv.reader(csvfile)
      for row in filereader:
        if row[0] in bootSteps:
          last_build[row[0]] = [row[1], row[2]]
    emulators,steps = getTestConfig(project, True)
    for k in last_build:
      if k != project and (k in steps or k in emulators):
        props[k] = last_build[k][0]
        props['file_list'] += ',' + last_build[k][1]
    return props

  def setProps():
    props = {}
    if api.path.exists(build_cache):
      with open(build_cache,'r') as csvfile:
        filereader = csv.reader(csvfile)
        for row in filereader:
          props[row[0]] = [row[1], row[2]]
    props[project] = [rev, file_list]
    with open(build_cache,'w') as csvfile:
      filewriter = csv.writer(csvfile)
      for line in props:
        filewriter.writerow([line, props[line][0], props[line][1]])

  try:
    api.python('Initialize Bot', init_bot_util_path,
               ['--build-dir', api.path['slave_build'],
                '--props', api.json.dumps(api.properties.thaw()),
                '--log-dir', log_dir],
               env=env)
  except api.step.StepFailure as f: # pragma: no cover
    # Not able to delete some files, it won't be the fault of emulator
    # not a stopper to run actual tests
    # so set status to "warning" and continue test
    f.result.presentation.status = api.step.WARNING

  api.python("Download and Unzip Images", image_util_path,
             ['--file', file_list,
              '--build-dir', build_dir],
             env=env)
  def PythonTestStep(description,
                     session_dir,
                     test_pattern,
                     cfg_file, cfg_filter, emulator_path):
    deferred_step_result = api.python(description, dotest_path,
                                      ['-l', 'INFO', '-exec', emulator_path,
                                       '-s', session_dir,
                                       '-p', test_pattern,
                                       '-c', api.path.join(script_root, 'config', cfg_file),
                                       '-n', buildername,
                                       '-f', cfg_filter],
                                      env=env, stderr=api.raw_io.output('err'))
    if not deferred_step_result.is_ok:
      stderr_output = deferred_step_result.get_error().result.stderr
      print stderr_output
      lines = [line for line in stderr_output.split('\n')
               if line.startswith('FAIL:') or line.startswith('TIMEOUT:')]
      for line in lines:
        api.step.active_result.presentation.logs[line] = ''
    else:
      print deferred_step_result.get_result().stderr
    if "CTS" in description:
      api.step.active_result.presentation.links['View XML'] = api.path.join("..", "..", "..",
                                                    "CTS_Result", buildername.replace(" ", "_"), 'build_%s-rev_%s' % (buildnum, rev), "testResult.xml")

  emulator_branch_to_use, steps_to_run = getTestConfig(project, is_cross_build)
  steps_to_run = [x for x in steps_to_run if api.properties.get(x)]
  with api.step.defer_results():
    for emu_branch in emulator_branch_to_use:
      emulator_path = api.path.join(emu_branch, 'tools', 'emulator')
      emu_desc = "sdk emulator" if emu_branch not in emulator_branches else emu_branch
      if not is_cts:
        for step in steps_to_run:
          step_data = bootSteps[step]
          PythonTestStep('Boot Test - %s System Image - %s' % (step_data.description, emu_desc),
                         api.path.join(log_dir, 'boot_test_%s_sysimage-%s' % (step_data.description, emu_desc)),
                         'test_boot.*',
                         'boot_cfg.csv',
                         step_data.filter,
                         emulator_path)
      elif project in emulator_branches:
        PythonTestStep('Run Emulator CTS Test',
                       api.path.join(log_dir, 'CTS_test'),
                       'test_cts.*',
                       'cts_cfg.csv',
                       '{}',
                       emulator_path)

    api.python("Zip and Upload Logs", log_util_path,
               ['--dir', log_dir,
                '--name', 'build_%s-rev_%s.zip' % (buildnum, rev),
                '--ip', MASTER_IP,
                '--user', MASTER_USER,
                '--dst', '%s%s/'% (api.properties['logs_dir'], buildername)],
                env=env)

  # If this build is triggered by scheduler, and it passes above steps
  # trigger build on cross builers
  if not is_cts and not is_cross_build:
    setProps()
    api.trigger(getProps())

def GenTests(api):
  yield (
    api.test('basic-win32') +
    api.platform.name('win') +
    api.platform.bits(32) +
    api.properties(
      mastername='client.adt',
      project='emu-master-dev',
      buildername='Win 7 32-bit HD 4400',
      lmp_revision='2460722',
      mnc_revision='2458059',
      emulator_image='/images/emu_gspoller_windows/sdk-repo-windows-tools-2344972.zip',
      lmp_system_image='/images/git_lmp-mr1-emu-dev-linux-sdk_google_phone_x86_64-sdk_addon/sdk-repo-linux-system-images-2460722.zip,images/git_lmp-mr1-emu-dev-linux-sdk_google_phone_x86-sdk_addon/sdk-repo-linux-system-images-2460722.zip',
      mnc_system_image='/images/git_mnc-emu-dev-linux-sdk_google_phone_x86_64-sdk_addon/sdk-repo-linux-system-images-2458059.zip,/images/git_mnc-emu-dev-linux-sdk_google_phone_x86-sdk_addon/sdk-repo-linux-system-images-2458059.zip',
      logs_dir='/home/slave_logs/',
      buildnumber='3077',
    )
  )

  yield (
    api.test('basic-win64') +
    api.platform.name('win') +
    api.platform.bits(64) +
    api.properties(
      mastername='client.adt',
      project='emu-master-dev',
      buildername='Win 7 64-bit HD 4400',
      lmp_revision='2460722',
      mnc_revision='2458059',
      emulator_image='/images/emu/sdk-repo-windows-tools-2344972.zip',
      lmp_system_image='/images/git_lmp-mr1-emu-dev-linux-sdk_google_phone_x86_64-sdk_addon/sdk-repo-linux-system-images-2460722.zip,images/git_lmp-mr1-emu-dev-linux-sdk_google_phone_x86-sdk_addon/sdk-repo-linux-system-images-2460722.zip',
      mnc_system_image='/images/git_mnc-emu-dev-linux-sdk_google_phone_x86_64-sdk_addon/sdk-repo-linux-system-images-2458059.zip,/images/git_mnc-emu-dev-linux-sdk_google_phone_x86-sdk_addon/sdk-repo-linux-system-images-2458059.zip',
      logs_dir='/home/slave_logs/',
      buildnumber='3077',
    )
  )

  yield (
    api.test('basic-mac') +
    api.platform.name('mac') +
    api.properties(
      mastername='client.adt',
      project='emu-master-dev',
      buildername='Mac 10.10.5 Iris Pro',
      lmp_revision='2460722',
      mnc_revision='2458059',
      emulator_image='/images/emu/sdk-repo-mac-tools-2344972.zip',
      lmp_system_image='/images/git_lmp-mr1-emu-dev-linux-sdk_google_phone_x86_64-sdk_addon/sdk-repo-linux-system-images-2460722.zip,images/git_lmp-mr1-emu-dev-linux-sdk_google_phone_x86-sdk_addon/sdk-repo-linux-system-images-2460722.zip',
      mnc_system_image='/images/git_mnc-emu-dev-linux-sdk_google_phone_x86_64-sdk_addon/sdk-repo-linux-system-images-2458059.zip,/images/git_mnc-emu-dev-linux-sdk_google_phone_x86-sdk_addon/sdk-repo-linux-system-images-2458059.zip',
      logs_dir='/home/slave_logs/',
      buildnumber='3077',
    )
  )

  yield (
    api.test('basic-linux') +
    api.platform.name('linux') +
    api.properties(
      mastername='client.adt',
      project='emu-master-dev',
      buildername='Ubuntu 15.04 Quadro K600',
      lmp_revision='2460722',
      mnc_revision='2458059',
      emulator_image='/images/emu/sdk-repo-linux-tools-2344972.zip',
      lmp_system_image='/images/git_lmp-mr1-emu-dev-linux-sdk_google_phone_x86_64-sdk_addon/sdk-repo-linux-system-images-2460722.zip,images/git_lmp-mr1-emu-dev-linux-sdk_google_phone_x86-sdk_addon/sdk-repo-linux-system-images-2460722.zip',
      mnc_system_image='/images/git_mnc-emu-dev-linux-sdk_google_phone_x86_64-sdk_addon/sdk-repo-linux-system-images-2458059.zip,/images/git_mnc-emu-dev-linux-sdk_google_phone_x86-sdk_addon/sdk-repo-linux-system-images-2458059.zip',
      logs_dir='/home/slave_logs/',
      buildnumber='3077',
    )
  )

  yield (
    api.test('boot-test-mnc-project') +
    api.platform.name('linux') +
    api.properties(
      mastername='client.adt',
      project='git_mnc-emu-dev',
      buildername='Ubuntu 15.04 Quadro K600',
      lmp_revision='2460722',
      mnc_revision='2458059',
      emulator_image='/images/emu/sdk-repo-linux-tools-2344972.zip',
      lmp_system_image='/images/git_lmp-mr1-emu-dev-linux-sdk_google_phone_x86_64-sdk_addon/sdk-repo-linux-system-images-2460722.zip,images/git_lmp-mr1-emu-dev-linux-sdk_google_phone_x86-sdk_addon/sdk-repo-linux-system-images-2460722.zip',
      mnc_system_image='/images/git_mnc-emu-dev-linux-sdk_google_phone_x86_64-sdk_addon/sdk-repo-linux-system-images-2458059.zip,/images/git_mnc-emu-dev-linux-sdk_google_phone_x86-sdk_addon/sdk-repo-linux-system-images-2458059.zip',
      logs_dir='/home/slave_logs/',
      buildnumber='3077',
    )
  )

  yield (
    api.test('boot-test-lmp-project') +
    api.platform.name('linux') +
    api.properties(
      mastername='client.adt',
      project='git_lmp-mr1-emu-dev',
      buildername='Ubuntu 15.04 Quadro K600',
      lmp_revision='2460722',
      mnc_revision='2458059',
      emulator_image='/images/emu/sdk-repo-linux-tools-2344972.zip',
      lmp_system_image='/images/git_lmp-mr1-emu-dev-linux-sdk_google_phone_x86_64-sdk_addon/sdk-repo-linux-system-images-2460722.zip,images/git_lmp-mr1-emu-dev-linux-sdk_google_phone_x86-sdk_addon/sdk-repo-linux-system-images-2460722.zip',
      mnc_system_image='/images/git_mnc-emu-dev-linux-sdk_google_phone_x86_64-sdk_addon/sdk-repo-linux-system-images-2458059.zip,/images/git_mnc-emu-dev-linux-sdk_google_phone_x86-sdk_addon/sdk-repo-linux-system-images-2458059.zip',
      logs_dir='/home/slave_logs/',
      buildnumber='3077',
    )
  )

  yield (
    api.test('boot-test-timeout-fail') +
    api.platform.name('linux') +
    api.properties(
      mastername='client.adt',
      project='emu-master-dev',
      buildername='Ubuntu 15.04 Quadro K600',
      lmp_revision='2460722',
      mnc_revision='2458059',
      emulator_image='/images/emu_gspoller_linux/sdk-repo-windows-tools-2344972.zip',
      lmp_system_image='/images/git_lmp-mr1-emu-dev-linux-sdk_google_phone_x86_64-sdk_addon/sdk-repo-linux-system-images-2460722.zip,images/git_lmp-mr1-emu-dev-linux-sdk_google_phone_x86-sdk_addon/sdk-repo-linux-system-images-2460722.zip',
      mnc_system_image='/images/git_mnc-emu-dev-linux-sdk_google_phone_x86_64-sdk_addon/sdk-repo-linux-system-images-2458059.zip,/images/git_mnc-emu-dev-linux-sdk_google_phone_x86-sdk_addon/sdk-repo-linux-system-images-2458059.zip',
      logs_dir='/home/slave_logs/',
      buildnumber='3077',
    ) +
    api.override_step_data('Boot Test - Public System Image',
                           api.raw_io.stream_output('TIMEOUT: foobar', 'stderr')
    ) +
    api.step_data('Boot Test - Public System Image', retcode=1)
  )

  yield (
    api.test('cts-test-timeout-fail') +
    api.platform.name('linux') +
    api.properties(
      mastername='client.adt',
      project='emu-master-dev',
      buildername='Ubuntu 15.04 Quadro K600',
      lmp_revision='2460722',
      mnc_revision='2458059',
      emulator_image='/images/emu_gspoller_linux/sdk-repo-windows-tools-2344972.zip',
      lmp_system_image='/images/git_lmp-mr1-emu-dev-linux-sdk_google_phone_x86_64-sdk_addon/sdk-repo-linux-system-images-2460722.zip,images/git_lmp-mr1-emu-dev-linux-sdk_google_phone_x86-sdk_addon/sdk-repo-linux-system-images-2460722.zip',
      mnc_system_image='/images/git_mnc-emu-dev-linux-sdk_google_phone_x86_64-sdk_addon/sdk-repo-linux-system-images-2458059.zip,/images/git_mnc-emu-dev-linux-sdk_google_phone_x86-sdk_addon/sdk-repo-linux-system-images-2458059.zip',
      logs_dir='/home/slave_logs/',
      buildnumber='3077',
    ) +
    api.override_step_data('Run Emulator CTS Test',
                           api.raw_io.stream_output('TIMEOUT: foobar', 'stderr')
    ) +
    api.step_data('Run Emulator CTS Test', retcode=1)
  )
