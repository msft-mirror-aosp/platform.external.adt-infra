#!/bin/bash

# This is used to execute multiple test runs of the system image UI tests
# ANDROID_SDK_ROOT must be defined externally
# usage: ./run_loop_ui_tests.sh $DISTRIB_DIR $ORI $TAG $NUM_RUNS

DISTRIB_DIR=$1
ORI=$2
TAG=$3
NUM_RUNS=$4

export ANDROID_EMU_ENABLE_CRASH_REPORTING="NO"

BUILDERNAME="Linux_gce"
FILTER_START='{"tag":"'
FILTER_MIDDLE='","ori":"'
FILTER_END='"}'
FILTER="${FILTER_START}${TAG}${FILTER_MIDDLE}${ORI}${FILTER_END}"
ANDROID_AVD_HOME="~/.android/avd"

echo "filter $FILTER"
echo "Using ADB"
which adb

echo "Running UI test for $API"
echo "Remove any existing AVDs"
echo "sudo rm -rf $ANDROID_AVD_HOME/*"
sudo rm -rf $ANDROID_AVD_HOME/*

export SNAPSHOT_DIR=$DISTRIB_DIR/snaps
mkdir -p $SNAPSHOT_DIR
echo "Save Snapshots to $SNAPSHOT_DIR"

SESSION_DIR=$DISTRIB_DIR/testlogs
mkdir -p $SESSION_DIR
echo "Session directory is $SESSION_DIR"

echo "Save Snapshot for $TAG at $SNAPSHOT_DIR"
echo "Run python -u $ADT_INFRA/emu_test/dotest.py --loglevel INFO --session_dir $SESSION_DIR --emulator $ANDROID_SDK_ROOT/emulator/emulator --file_pattern 'test_ui.*' --config_file $ADT_INFRA/emu_test/config/ui_cfg_byob.csv --buildername $BUILDERNAME --filter $FILTER --skip-adb-perf --save_snapshot"
python -u $ADT_INFRA/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $ANDROID_SDK_ROOT/emulator/emulator --file_pattern 'test_ui.*' --config_file $ADT_INFRA/emu_test/config/ui_cfg_byob.csv --buildername $BUILDERNAME --filter $FILTER --skip-adb-perf --save_snapshot

i=1

echo "$i is less than $NUM_RUNS?"
while [[ $i -le $NUM_RUNS ]]
do
    TEST_DIR=UI_TEST_$i
    echo "Test directory is $TEST_DIR"

    echo "Run python -u $ADT_INFRA/emu_test/dotest.py --loglevel INFO --session_dir $SESSION_DIR --emulator $ANDROID_SDK_ROOT/emulator/emulator --test_dir $TEST_DIR --file_pattern 'test_ui.*' --config_file $ADT_INFRA/emu_test/config/ui_cfg_byob.csv --buildername $BUILDERNAME --filter $FILTER --skip-adb-perf --load-snapshot $NUM_RUNS times"
    python -u $ADT_INFRA/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $ANDROID_SDK_ROOT/emulator/emulator --test_dir $TEST_DIR --file_pattern 'test_ui.*' --config_file $ADT_INFRA/emu_test/config/ui_cfg_byob.csv --buildername $BUILDERNAME --filter $FILTER --skip-adb-perf --load-snapshot
    i=$((i + 1))
done

echo "UI test completed" 
