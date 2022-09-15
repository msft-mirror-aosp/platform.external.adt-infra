#!/bin/bash
# Copyright 2020 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This is used to run AVD and console emulator tests.
# This will be invoked by aosp-emu-master-dev.
. $(dirname "$0")/common.sh

DISTRIB_DIR=$1
TEST_DIR=$(dirname "$0")/..

# Status code, a 0 indicates we had no timouts.
STATUS=0
SESSION_DIR=$DISTRIB_DIR/testlogs
BUILD_DIR="out/prebuilt_cached/builds"
EMULATOR_EXE=$SESSION_DIR/emu-master-dev/emulator/emulator

export ANDROID_HOME=$SDK_EMULATOR
export ANDROID_SDK_ROOT=$SDK_EMULATOR
export ANDROID_EMU_ENABLE_CRASH_REPORTING="NO"

BUILDERNAME="Linux_gce"
OS="linux"
if [[ $OSTYPE == *"darwin"* ]]; then
    BUILDERNAME="Mac"
    OS="darwin"
else
    ps cax | grep vnc >/dev/null
    if [ $? -eq 1 ]; then
        log "Start VNC server"
        vncserver
    fi
    AVAILABLE_DISPLAYS=$(cd /tmp/.X11-unix && for x in X*; do echo ":${x#X}"; done)
    export DISPLAY=$(echo ${AVAILABLE_DISPLAYS} | cut -d ' ' -f 1)
    log "We have the following displays available: ${AVAILABLE_DISPLAYS}, using ${DISPLAY}"
fi

# Let's log a lot.
set_verbosity 2

# Make sure all the expected variables have been set.
check_vars SDK_EMULATOR ANDROID_AVD_HOME ANDROID_SDK_ROOT ANDROID_HOME SESSION_DIR EMULATOR_EXE ANDROID_EMU_ENABLE_CRASH_REPORTING PYTHON

# Make sure we remove adb when we are exiting.
# Note that the value of "$?" after the trap action
# completes shall be the value it had before trap was invoked.
trap "terminate_adb" EXIT QUIT INT HUP

log "Update emulator, not used, just for the purpose of sys img dependencies"
run $ANDROID_HOME/tools/bin/sdkmanager --channel=3 --install emulator


log "Deploy emulator"
run mkdir -p $SESSION_DIR
run mkdir -p $SESSION_DIR/emu-master-dev
run unzip -o $BUILD_DIR/sdk-repo-$OS-emulator-[0-9]*.zip -d $SESSION_DIR/emu-master-dev || panic "Unable to unzip required files."

log "activate virtualenv"
activate_virtualenv $TEST_DIR/utils

# Run the android-studio embedded emulator tests
export ANDROID_EMU_ENABLE_CRASH_REPORTING="YES"
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
clean_avds
run_test "Embedded tests" external/adt-infra/pytest/test_embedded/run_tests.sh --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --warn $(is_presubmit $BID)

export ANDROID_EMU_ENABLE_CRASH_REPORTING="NO"
clean_avds
run_test "Console tests" $PYTHON -u $TEST_DIR/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $EMULATOR_EXE --test_dir Console_test --file_pattern 'test_console.*' --config_file $TEST_DIR/config/console_cfg_byob.csv --buildername $BUILDERNAME --headless

log "deactivate virtualenv"
deactivate_virtualenv

log "Remove deployed emulator"
run rm -rf $SESSION_DIR/emu-master-dev

log "Cleanup prebuilts"
run rm -rf /buildbot/prebuilt/*

log "Remove any empty file"
find $SESSION_DIR -size 0 -delete || log "No empty files were deleted."

exit $STATUS
