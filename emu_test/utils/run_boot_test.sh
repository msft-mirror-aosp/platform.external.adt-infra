#!/bin/bash

# This is used to run system image boot tests.
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

SESSION_DIR=$DISTRIB_DIR/testlogs
mkdir -p $SESSION_DIR

log "activate virtualenv"
activate_virtualenv $ADT_INFRA/emu_test/utils

python -u $ADT_INFRA/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $ANDROID_SDK_ROOT/emulator/emulator --test_dir BOOT_test --file_pattern 'test_boot.*' --config_file $ADT_INFRA/emu_test/config/boot_cfg_byob.csv --buildername $BUILDERNAME --filter $FILTER --generate_xml --headless

log "deactivate virtualenv"
deactivate_virtualenv

find $SESSION_DIR -size  0 -print0 |xargs -0 rm --

echo "Boot test completed"
