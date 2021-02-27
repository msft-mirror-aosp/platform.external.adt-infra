#!/bin/bash

# This is used to build and test emulator binaries.
# This will be invoked by aosp-emu-master-dev.
. $(dirname "$0")/common.sh

OUT_DIR=$1
DISTRIB_DIR=$2
BID=$3
CPU=$4
USE_QTWEBENGINE=$5

TEST_DIR=$(dirname "$0")/..

# Let's log the commands.
set_verbosity 2

# Make sure all the expected variables have been set.
check_vars ANDROID_AVD_HOME SDK_EMULATOR  DISTRIB_DIR

export ANDROID_HOME=$SDK_EMULATOR
export ANDROID_SDK_ROOT=$SDK_EMULATOR
export ANDROID_EMU_ENABLE_CRASH_REPORTING="NO"


BUILDERNAME="Linux_gce"
OS="linux"
if [[ $OSTYPE == *"darwin"* ]]
then
    BUILDERNAME="Mac"
    OS="darwin"
else
    ps cax | grep vnc > /dev/null
    if [ $? -eq 1 ]; then
        log "Start VNC server"
        vncserver
    fi
fi

SESSION_DIR=$DISTRIB_DIR/testlogs
mkdir -p $SESSION_DIR

# Make sure we remove adb when we are exiting.
# Note that the value of "$?" after the trap action
# completes shall be the value it had before trap was invoked.
trap "terminate_adb" EXIT QUIT INT HUP

log "Build Emulator"

QTWEBENGINE_ARG=
if [[ $USE_QTWEBENGINE == "qtwebengine" ]]; then
    QTWEBENGINE_ARG="--qtwebengine"
fi

python tools/buildSrc/servers/build_tools.py --out_dir $OUT_DIR --dist_dir $DISTRIB_DIR --build-id $BID $QTWEBENGINE_ARG || panic "build failure"

exit 0

# Contains what we distribute to the world.
run unzip -o $DISTRIB_DIR/sdk-repo-$OS-emulator-[P,0-9]*.zip -d $SESSION_DIR/emu-master-dev || panic "Unable to unzip required files."

# Contains all the unit tests, symbols, debug_information and testing tools needed for some e2e tests.
run unzip -o $DISTRIB_DIR/sdk-repo-$OS-debug-emulator-[P,0-9]*.zip -d $SESSION_DIR/emu-master-dev-dbg

log "Remove any existing AVDs in ${ANDROID_AVD_HOME}"
run rm -rf $ANDROID_AVD_HOME/*

log "activate virtualenv"
activate_virtualenv

# Run the android-studio embedded emulator tests
#run_test "Embedded tests" external/adt-infra/emu_test/test_embedded/run_tests.sh --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator
#check_test_succeed embedded_test

run_test "Boot_test" $PYTHON -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Boot_test --file_pattern 'test_boot.*' --config_file external/adt-infra/emu_test/config/boot_cfg_byob.csv --buildername $BUILDERNAME --filter '{"ori":"public"}' --generate_xml
check_test_succeed Boot_test

export ANDROID_EMU_ENABLE_CRASH_REPORTING="YES"
run_test "Running Crash tests" $PYTHON -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Crash_test --file_pattern 'test_crash.*' --config_file external/adt-infra/emu_test/config/crash_cfg_byob.csv --buildername $BUILDERNAME  --generate_xml --skip-adb-perf
check_test_succeed Crash_test
export ANDROID_EMU_ENABLE_CRASH_REPORTING="NO"

# These are a bit flaky
# run_test "Running Snapshot save/load tests" $PYTHON -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Snapshot_test --file_pattern 'psq_test.*' --config_file external/adt-infra/emu_test/config/psq_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf

log "deactivate virtualenv"
deactivate_virtualenv

log "Remove any empty file in $SESSION_DIR"
find $SESSION_DIR -size 0 -delete || log "Did not remove any empty files."

log "Success!"
