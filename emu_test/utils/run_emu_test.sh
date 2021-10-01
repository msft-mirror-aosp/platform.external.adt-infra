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

clean_avds
run_test "Boot_test" $PYTHON -u $TEST_DIR/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $EMULATOR_EXE --test_dir Boot_test --file_pattern 'test_boot.*' --config_file $TEST_DIR/config/boot_cfg_byob.csv --buildername $BUILDERNAME --filter '{"ori":"public"}' --generate_xml --headless

if [[ $OSTYPE != *"darwin"* ]]; then
    log "Generate Perf Data"
    # 3.8888889 hours?
    run_timeout 14000 $PYTHON -u $TEST_DIR/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $EMULATOR_EXE --test_dir Perf_test --file_pattern 'test_perf.*' --config_file $TEST_DIR/config/perf_cfg_byob.csv --buildername $BUILDERNAME --filter '{"ori":"public-perf"}' --generate_perf

    run_test "Perf test api 28" $PYTHON -u $TEST_DIR/utils/perf_stats.py --log_dir $SESSION_DIR/Perf_test --api 28
    run_test "Perf test api 29" $PYTHON -u $TEST_DIR/utils/perf_stats.py --log_dir $SESSION_DIR/Perf_test --api 29 --metric_tag 29

    log "Zip perf data"
    sh -c "cd $SESSION_DIR && zip -rm $DISTRIB_DIR/perfgate_data.zip Perf_test/test.outputs/*.json"

    if [[ ! -f $DISTRIB_DIR/perfgate_data.zip ]]; then
        STATUS=1
        warn "Perf zip fail"
    fi

    run_test "snapshot tests" $PYTHON -u $TEST_DIR/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $EMULATOR_EXE --test_dir snapshot_test --file_pattern 'test_snapshot.*' --config_file $TEST_DIR/config/snapshot_cfg_byob.csv --buildername $BUILDERNAME --generate_xml --headless
    run_test "grpc tests" $PYTHON -u $TEST_DIR/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $EMULATOR_EXE --test_dir grpc_test --file_pattern 'test_grpc.*' --config_file $TEST_DIR/config/snapshot_cfg_byob.csv --buildername $BUILDERNAME --generate_xml --headless
fi

# Run the android-studio embedded emulator tests
export ANDROID_EMU_ENABLE_CRASH_REPORTING="YES"
clean_avds
run_test "Embedded tests" external/adt-infra/emu_test/test_embedded/run_tests.sh --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --warn $(is_presubmit $BID)
if [[ $(is_presubmit $BID) == "true" ]]; then
    # Ignore failures until the tests have stabilised.
    # See b/183949465 for details.
    # check_test_succeed embedded_test
    echo "Ignoring potential errors due to  b/183949465"
fi

export ANDROID_EMU_ENABLE_CRASH_REPORTING="YES"
run_test "Running Crash tests" $PYTHON -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Crash_test --file_pattern 'test_crash.*' --config_file external/adt-infra/emu_test/config/crash_cfg_byob.csv --buildername $BUILDERNAME  --generate_xml --skip-adb-perf

export ANDROID_EMU_ENABLE_CRASH_REPORTING="NO"
clean_avds
run_test "Console tests" $PYTHON -u $TEST_DIR/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $EMULATOR_EXE --test_dir Console_test --file_pattern 'test_console.*' --config_file $TEST_DIR/config/console_cfg_byob.csv --buildername $BUILDERNAME --headless

clean_avds
run_test "AVD tests" $PYTHON -u $TEST_DIR/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $EMULATOR_EXE --test_dir AVD_test --file_pattern '*launch_avd*.*' --config_file $TEST_DIR/config/avd_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf --generate_xml --headless

clean_avds
run_test "psq snapshot tests" $PYTHON -u $TEST_DIR/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $EMULATOR_EXE --test_dir psq_snapshot_test --file_pattern 'psq_test.*' --config_file $TEST_DIR/config/psq_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf --generate_xml --headless

clean_avds
#run_test "Icebox tests" $PYTHON -u $TEST_DIR/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $EMULATOR_EXE --test_dir Icebox_test --file_pattern 'test_icebox.*' --config_file $TEST_DIR/config/icebox_cfg.csv --buildername $BUILDERNAME --skip-adb-perf --generate_xml --headless

log "deactivate virtualenv"
deactivate_virtualenv

log "Remove deployed emulator"
run rm -rf $SESSION_DIR/emu-master-dev

log "Cleanup prebuilts"
run rm -rf /buildbot/prebuilt/*

log "Remove any empty file"
find $SESSION_DIR -size 0 -delete || log "No empty files were deleted."

exit $STATUS
