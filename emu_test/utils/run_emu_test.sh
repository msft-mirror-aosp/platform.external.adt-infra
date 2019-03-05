#!/bin/bash

# This is used to run AVD and console emulator tests.
# This will be invoked by aosp-emu-master-dev.

DIST_DIR=$1

export ANDROID_HOME=$SDK_EMULATOR
export ANDROID_SDK_ROOT=$SDK_EMULATOR

BUILDERNAME="Linux_gce"
OS="linux"
if [[ $OSTYPE == *"darwin"* ]]
then
    BUILDERNAME="Mac"
    OS="darwin"
else
    ps cax | grep vnc > /dev/null
    if [ $? -eq 1 ]; then
        echo "Start VNC server"
        vncserver
    fi
fi

SESSION_DIR=$DIST_DIR/testlogs
mkdir -p $SESSION_DIR

echo "Deploy emulator"
echo "Run mkdir -p $SESSION_DIR/emu-master-dev"
mkdir -p $SESSION_DIR/emu-master-dev

BUILD_DIR="out/prebuilt_cached/builds"

echo "Run unzip -o $BUILD_DIR/sdk-repo-$OS-emulator-[0-9]*.zip -d $SESSION_DIR/emu-master-dev"
unzip -o $BUILD_DIR/sdk-repo-$OS-emulator-[0-9]*.zip -d $SESSION_DIR/emu-master-dev

echo "Update SDK"
echo "Run $ANDROID_HOME/tools/bin/sdkmanager --update"
(yes | $ANDROID_HOME/tools/bin/sdkmanager --licenses) & sleep 10 ; kill $!
pkill yes
$ANDROID_HOME/tools/bin/sdkmanager --update

echo "Running Boot tests"
echo "Remove any existing AVDs"
echo "sudo rm -rf $ANDROID_AVD_HOME/*"
sudo rm -rf $ANDROID_AVD_HOME/*

echo "Run python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Boot_test --file_pattern 'test_boot.*' --config_file external/adt-infra/emu_test/config/boot_cfg_byob.csv --buildername $BUILDERNAME --filter '{"ori": "public"}' --generate_xml"
python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Boot_test --file_pattern 'test_boot.*' --config_file external/adt-infra/emu_test/config/boot_cfg_byob.csv --buildername $BUILDERNAME --filter '{"ori": "public"}' --generate_xml

echo "Zip perf data"
sh -c "cd $SESSION_DIR && zip -rm Boot_test/test.outputs/outputs.zip Boot_test/test.outputs/*.json
sh -c "cd $SESSION_DIR && zip -rm $DIST_DIR/perfgate_data.zip Boot_test/test.outputs/*"
rm -rf $SESSION_DIR/Boot_test/test.outputs

if [[ $OSTYPE != *"darwin"* ]]
then
    echo "Running AVD tests"
    echo "Remove any existing AVDs"
    echo "sudo rm -rf $ANDROID_AVD_HOME/*"
    sudo rm -rf $ANDROID_AVD_HOME/*

    echo "Run python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir AVD_test --file_pattern '*launch_avd*.*' --config_file external/adt-infra/emu_test/config/avd_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf --generate_xml"
    python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir AVD_test --file_pattern '*launch_avd*.*' --config_file external/adt-infra/emu_test/config/avd_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf --generate_xml
fi

echo "Running Console tests"
echo "Remove any existing AVDs"
echo "sudo rm -rf $ANDROID_AVD_HOME/*"
sudo rm -rf $ANDROID_AVD_HOME/*

echo "Run python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Console_test --file_pattern 'test_console.*' --config_file external/adt-infra/emu_test/config/console_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf"
python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Console_test --file_pattern 'test_console.*' --config_file external/adt-infra/emu_test/config/console_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf

echo "Remove deployed emulator"
echo "Run rm -rf $SESSION_DIR/emu-master-dev"
rm -rf $SESSION_DIR/emu-master-dev

echo "Cleanup prebuilts"
rm -rf /buildbot/prebuilt/*

echo "Remove any empty file"
find $SESSION_DIR -size  0 -print0 |xargs -0 rm --

exit 0
