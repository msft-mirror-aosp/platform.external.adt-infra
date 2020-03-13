#!/bin/bash

# This is used to run ADB tests.
# This will be invoked by system image source.
#  {src}/platform_testing/emu_test/run_test.sh

DISTRIB_DIR=$1
STATUS=0

export PATH=$PATH:$ANDROID_SDK_ROOT/platform-tools

echo "using ADB"
which adb

export ANDROID_EMU_ENABLE_CRASH_REPORTING="NO"

BUILDERNAME="Linux_gce"
TIMEOUT_CMD="timeout"
if [[ $OSTYPE == *"darwin"* ]]
then
    BUILDERNAME="Mac"
    TIMEOUT_CMD="gtimeout"
else
    ps cax | grep vnc > /dev/null
    if [ $? -eq 1 ]; then
        echo "Start VNC server"
        vncserver
    fi
fi

echo "Running ADB test"
echo "Remove any existing AVDs"
echo "sudo rm -rf $ANDROID_AVD_HOME/*"
sudo rm -rf $ANDROID_AVD_HOME/*

SESSION_DIR=$DISTRIB_DIR/testlogs
mkdir -p $SESSION_DIR

export GENERAL_TESTS_DIR=$DISTRIB_DIR/general-tests/host/testcases

echo "Run python -u $ADT_INFRA/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $ANDROID_SDK_ROOT/emulator/emulator --test_dir ADB_test --file_pattern 'test_adb.*' --config_file $ADT_INFRA/emu_test/config/adb_cfg_byob.csv --buildername $BUILDERNAME --filter '{"ori": "public"}' --headless"
$TIMEOUT_CMD 4200 python -u $ADT_INFRA/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $ANDROID_SDK_ROOT/emulator/emulator --test_dir ADB_test --file_pattern 'test_adb.*' --config_file $ADT_INFRA/emu_test/config/adb_cfg_byob.csv --buildername $BUILDERNAME --filter '{"ori": "public"}' --headless

if [[ ! -f $SESSION_DIR/ADB_test/test_adbTestResult.xml ]]
then
    STATUS=1
fi

echo "Remove any empty file"
find $SESSION_DIR -size  0 -print0 |xargs -0 rm --

echo "ADB test completed"
exit $STATUS
