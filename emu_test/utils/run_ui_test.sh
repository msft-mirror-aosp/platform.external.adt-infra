#!/bin/bash

# This is used to run system image UI tests.
# This will be invoked by devtools-test branch source.
#  {src}/test/run_sys_img_test.sh

set -x
echo $@
env

. $(dirname "$0")/common.sh

DISTRIB_DIR=$1
FILTER=$2

export ANDROID_EMU_ENABLE_CRASH_REPORTING="NO"

BUILDERNAME="Linux_gce"
if [[ $OSTYPE == *"darwin"* ]]
then
    BUILDERNAME="Mac"
else
    ps cax | grep vnc > /dev/null
    if [ $? -eq 1 ]; then
        echo "Start VNC server"
        vncserver
    fi
fi

rm -rf $ANDROID_AVD_HOME/*

export SNAPSHOT_DIR=$DISTRIB_DIR/snaps
mkdir -p $SNAPSHOT_DIR

SESSION_DIR=$DISTRIB_DIR/testlogs
TEST_DIR=UI_TEST
mkdir -p $SESSION_DIR

log "activate virtualenv"
activate_virtualenv

echo "Save Snapshots $SNAPSHOT_DIR"
python -u $ADT_INFRA/emu_test/dotest.py --loglevel INFO --session_dir $SESSION_DIR --emulator $ANDROID_SDK_ROOT/emulator/emulator --test_dir $TEST_DIR --file_pattern 'test_ui.*' --config_file $ADT_INFRA/emu_test/config/ui_cfg_byob.csv --buildername $BUILDERNAME --filter $FILTER --skip-adb-perf --save_snapshot --headless
rm -rf $SESSION_DIR/$TEST_DIR

python -u $ADT_INFRA/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $ANDROID_SDK_ROOT/emulator/emulator --test_dir $TEST_DIR --file_pattern 'test_ui.*' --config_file $ADT_INFRA/emu_test/config/ui_cfg_byob.csv --buildername $BUILDERNAME --filter $FILTER --skip-adb-perf --load_snapshot --headless

log "deactivate virtualenv"
deactivate_virtualenv

rm -rf $SNAPSHOT_DIR

find $SESSION_DIR -size  0 -print0 |xargs -0 rm --

echo "UI test completed"
