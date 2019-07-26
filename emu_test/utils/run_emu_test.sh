#!/bin/bash

# This is used to run AVD and console emulator tests.
# This will be invoked by aosp-emu-master-dev.

DISTRIB_DIR=$1
STATUS=0

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
        echo "Start VNC server"
        vncserver
    fi
fi

SESSION_DIR=$DISTRIB_DIR/testlogs
mkdir -p $SESSION_DIR

echo "Deploy emulator"
echo "Run mkdir -p $SESSION_DIR/emu-master-dev"
mkdir -p $SESSION_DIR/emu-master-dev

BUILD_DIR="out/prebuilt_cached/builds"

echo "Run unzip -o $BUILD_DIR/sdk-repo-$OS-emulator-[0-9]*.zip -d $SESSION_DIR/emu-master-dev"
unzip -o $BUILD_DIR/sdk-repo-$OS-emulator-[0-9]*.zip -d $SESSION_DIR/emu-master-dev

echo "Remove any existing AVDs"
echo "rm -rf $ANDROID_AVD_HOME/*"
rm -rf $ANDROID_AVD_HOME/*

echo "Generate Perf Data"
echo "Run python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Perf_test --file_pattern 'test_perf.*' --config_file external/adt-infra/emu_test/config/perf_cfg_byob.csv --buildername $BUILDERNAME --filter '{"ori": "public-perf"}' --generate_perf"
python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Perf_test --file_pattern 'test_perf.*' --config_file external/adt-infra/emu_test/config/perf_cfg_byob.csv --buildername $BUILDERNAME --filter '{"ori": "public-perf"}' --generate_perf

echo "Run python -u external/adt-infra/emu_test/utils/perf_stats.py --log_dir $SESSION_DIR/Perf_test"
python -u external/adt-infra/emu_test/utils/perf_stats.py --log_dir $SESSION_DIR/Perf_test

echo "Zip perf data"
sh -c "cd $SESSION_DIR && zip -rm Perf_test/test.outputs/outputs.zip Perf_test/test.outputs/*.json"
sh -c "cd $SESSION_DIR && zip -rm $DISTRIB_DIR/perfgate_data.zip Perf_test/test.outputs/*"

if [[ ! -f $DISTRIB_DIR/perfgate_data.zip ]]
then
    STATUS=1
fi

echo "Running Boot tests"
echo "Run python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Boot_test --file_pattern 'test_boot.*' --config_file external/adt-infra/emu_test/config/boot_cfg_byob.csv --buildername $BUILDERNAME --filter '{"ori": "public"}' --generate_xml"
python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Boot_test --file_pattern 'test_boot.*' --config_file external/adt-infra/emu_test/config/boot_cfg_byob.csv --buildername $BUILDERNAME --filter '{"ori": "public"}' --generate_xml

if [[ ! -f $SESSION_DIR/Boot_test/test_report.xml ]]
then
    STATUS=1
fi

echo "Running Console tests"
echo "Remove any existing AVDs"
echo "rm -rf $ANDROID_AVD_HOME/*"
rm -rf $ANDROID_AVD_HOME/*

echo "Run python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Console_test --file_pattern 'test_console.*' --config_file external/adt-infra/emu_test/config/console_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf"
python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Console_test --file_pattern 'test_console.*' --config_file external/adt-infra/emu_test/config/console_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf

if [[ ! -f $SESSION_DIR/Console_test/test_consoleTestResult.xml ]]
then
    STATUS=1
fi

echo "Running AVD tests"
echo "Remove any existing AVDs"
echo "rm -rf $ANDROID_AVD_HOME/*"
rm -rf $ANDROID_AVD_HOME/*

echo "Run python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir AVD_test --file_pattern '*launch_avd*.*' --config_file external/adt-infra/emu_test/config/avd_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf --generate_xml"
python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir AVD_test --file_pattern '*launch_avd*.*' --config_file external/adt-infra/emu_test/config/avd_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf --generate_xml

if [[ ! -f $SESSION_DIR/AVD_test/test_report.xml ]]
then
    STATUS=1
fi

echo "Running psq snapshot tests"
echo "Remove any existing AVDs"
echo "rm -rf $ANDROID_AVD_HOME/*"
rm -rf $ANDROID_AVD_HOME/*

echo "Run python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Snapshot_test --file_pattern 'psq_test.*' --config_file external/adt-infra/emu_test/config/psq_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf --generate_xml"
python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Snapshot_test --file_pattern 'psq_test.*' --config_file external/adt-infra/emu_test/config/psq_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf --generate_xml

if [[ ! -f $SESSION_DIR/Snapshot_test/test_report.xml ]]
then
    STATUS=1
fi

echo "Remove deployed emulator"
echo "Run rm -rf $SESSION_DIR/emu-master-dev"
rm -rf $SESSION_DIR/emu-master-dev

echo "Cleanup prebuilts"
rm -rf /buildbot/prebuilt/*

echo "Remove any empty file"
find $SESSION_DIR -size  0 -print0 |xargs -0 rm --

exit $STATUS
