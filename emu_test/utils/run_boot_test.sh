#!/bin/bash

# This is used to run system image UI tests.
# This will be invoked by system image source.
#  {src}/platform_testing/ui_test/run_ui_test.sh

DIST_DIR=$1
ORI=$2
API=$3

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

echo "Running BOOT test for $API"
echo "Remove any existing AVDs"
echo "sudo rm -rf $ANDROID_AVD_HOME/*"
sudo rm -rf $ANDROID_AVD_HOME/*

SESSION_DIR=$DIST_DIR/testlogs
mkdir -p $SESSION_DIR

FILTER={\"ori\":\"$ORI\"}

echo "Run python -u $ADT_INFRA/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $ANDROID_SDK_ROOT/emulator/emulator --test_dir BOOT_test --file_pattern 'test_boot.*' --config_file $ADT_INFRA/emu_test/config/boot_cfg_byob.csv --buildername $BUILDERNAME --filter $FILTER --generate_xml"
python -u $ADT_INFRA/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $ANDROID_SDK_ROOT/emulator/emulator --test_dir BOOT_test --file_pattern 'test_boot.*' --config_file $ADT_INFRA/emu_test/config/boot_cfg_byob.csv --buildername $BUILDERNAME --filter $FILTER --generate_xml

echo "Remove any empty file"
find $SESSION_DIR -size  0 -print0 |xargs -0 rm --

echo "Boot test completed"
