#!/bin/bash

# This is used to run AVD and console emulator tests.
# This will be invoked by aosp-emu-master-dev.

DIST_DIR=$1
BUILD_NUM=$2

echo "Starting build for Emulator"
tools/buildSrc/servers/build_tools.sh out $DIST_DIR $BUILD_NUM 80
if [ $? != 0 ];
then
    exit 1
fi

SESSION_DIR=$DIST_DIR/gtest
mkdir -p $SESSION_DIR

echo "Deploy emulator"
echo "Run mkdir -p $SESSION_DIR/emu-master-dev"
mkdir -p $SESSION_DIR/emu-master-dev

echo "Run unzip -o $DIST_DIR/sdk-repo-linux-emulator-*.zip -d $SESSION_DIR/emu-master-dev"
unzip -o $DIST_DIR/sdk-repo-linux-emulator-*.zip -d $SESSION_DIR/emu-master-dev

echo "Update SDK"
echo "Run $ANDROID_HOME/tools/bin/sdkmanager --update"
$ANDROID_HOME/tools/bin/sdkmanager --update

echo "Running Boot tests"
echo "Run python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir boot_test_public_sysimage-emu-master-dev --file_pattern 'test_boot.*' --config_file external/adt-infra/emu_test/config/boot_cfg_gce.csv --buildername 'Ubuntu 16.04 Thinkpad 2017' --filter '{"ori": "public"}'"
python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir boot_test_public_sysimage-emu-master-dev --file_pattern 'test_boot.*' --config_file external/adt-infra/emu_test/config/boot_cfg_gce.csv --buildername 'Ubuntu 16.04 Thinkpad 2017' --filter '{"ori": "public"}'

echo "Running AVD tests"
echo "Run python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir AVD_test --file_pattern '*launch_avd*.*' --config_file external/adt-infra/emu_test/config/avd_cfg_gce.csv --buildername 'Ubuntu 16.04 Thinkpad 2017' --skip-adb-perf"
python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir AVD_test --file_pattern '*launch_avd*.*' --config_file external/adt-infra/emu_test/config/avd_cfg_gce.csv --buildername 'Ubuntu 16.04 Thinkpad 2017' --skip-adb-perf

echo "Running Console tests"
echo "Run python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Console_test --file_pattern 'test_console.*' --config_file external/adt-infra/emu_test/config/console_cfg_gce.csv --buildername 'Ubuntu 12.04 HD Graphics 4000' --skip-adb-perf"
python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Console_test --file_pattern 'test_console.*' --config_file external/adt-infra/emu_test/config/console_cfg_gce.csv --buildername 'Ubuntu 12.04 HD Graphics 4000' --skip-adb-perf

echo "Remove deployed emulator"
echo "Run rm -rf $SESSION_DIR/emu-master-dev"
rm -rf $SESSION_DIR/emu-master-dev

exit 0
