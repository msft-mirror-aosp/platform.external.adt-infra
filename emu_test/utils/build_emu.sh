#!/bin/bash

# This is used to build and test emulator binaries.
# This will be invoked by aosp-emu-master-dev.
. $(dirname "$0")/common.sh

OUT_DIR=$1
DISTRIB_DIR=$2
export BID=$3
export CPU=$4
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

PYTHON=python

# Prefer python3 if it is available.
if command -v python3 &>/dev/null; then
  log "Using python 3"
  PYTHON=python3
  $PYTHON -m venv $OUT_DIR/venv
  [ -e $OUT_DIR/venv/bin/pip ] && $OUT_DIR/venv/bin/pip install --upgrade pip
  [ -e $OUT_DIR/venv/bin/pip ] && $OUT_DIR/venv/bin/pip install --upgrade setuptools
else
  log "Using python 2.. This is no longer officially supported!"
  log "https://python3statement.org/"
fi


log "Build Emulator"

QTWEBENGINE_ARG=
if [[ $USE_QTWEBENGINE == "qtwebengine" ]]; then
    QTWEBENGINE_ARG="--qtwebengine"
fi


if [ -d /mnt/tmpfs ];
then
    # Test to use tmpfs for compilation. This should result in:
    # 1. Re-use of ccache as the paths will all be the same.
    # 2. Fast access as we are using memory v.s. disk.
    # 3. Bots have > 100gb of memory, build dir takes +/- 16gb
    rm -rf /mnt/tmpfs/build
    $PYTHON tools/buildSrc/servers/build_tools.py --out_dir /mnt/tmpfs/build --dist_dir $DISTRIB_DIR --build-id $BID $QTWEBENGINE_ARG || panic "build failure"
else
    $PYTHON tools/buildSrc/servers/build_tools.py --out_dir $OUT_DIR --dist_dir $DISTRIB_DIR --build-id $BID $QTWEBENGINE_ARG || panic "build failure"
fi

# Contains what we distribute to the world.
run unzip -o $DISTRIB_DIR/sdk-repo-$OS-emulator-[P,0-9]*.zip -d $SESSION_DIR/emu-master-dev || panic "Unable to unzip required files."

log "Remove any existing AVDs in ${ANDROID_AVD_HOME}"
run rm -rf $ANDROID_AVD_HOME/*

log "activate virtualenv"
activate_virtualenv $TEST_DIR/utils

export ANDROID_EMU_ENABLE_CRASH_REPORTING="NO"
run_test "Boot_test" $PYTHON -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Boot_test --file_pattern 'test_boot.*' --config_file external/adt-infra/emu_test/config/boot_cfg_byob.csv --buildername $BUILDERNAME --filter '{"ori":"public"}' --generate_xml
check_test_succeed Boot_test


# These are a bit flaky
# run_test "Running Snapshot save/load tests" $PYTHON -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Snapshot_test --file_pattern 'psq_test.*' --config_file external/adt-infra/emu_test/config/psq_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf

log "deactivate virtualenv"
deactivate_virtualenv

log "Remove deployed emulator builds"
rm -rf $SESSION_DIR/emu-master-dev*

log "Remove any empty file in $SESSION_DIR"
find $SESSION_DIR -size 0 -delete || log "Did not remove any empty files."

log "Success!"
