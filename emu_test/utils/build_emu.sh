#!/bin/bash

# This is used to build and test emulator binaries.
# This will be invoked by aosp-emu-master-dev.

OUT_DIR=$1
DISTRIB_DIR=$2
BID=$3
CPU=$4

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

echo "Build Emulator"
echo "tools/buildSrc/servers/build_tools.py --out_dir $OUT_DIR --dist_dir $DISTRIB_DIR --build-id $BID"
tools/buildSrc/servers/build_tools.py --out_dir $OUT_DIR --dist_dir $DISTRIB_DIR --build-id $BID

if [[ $? -ne 0 ]]
then
    exit 1
fi

echo "Run unzip -o $DISTRIB_DIR/sdk-repo-$OS-emulator-[P,0-9]*.zip -d $SESSION_DIR/emu-master-dev"
unzip -o $DISTRIB_DIR/sdk-repo-$OS-emulator-[P,0-9]*.zip -d $SESSION_DIR/emu-master-dev

echo "Running Boot tests"
echo "Remove any existing AVDs"
echo "sudo rm -rf $ANDROID_AVD_HOME/*"
sudo rm -rf $ANDROID_AVD_HOME/*

echo "Run python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Boot_test --file_pattern 'test_boot.*' --config_file external/adt-infra/emu_test/config/boot_cfg_byob.csv --buildername $BUILDERNAME --filter '{"ori": "public"}' --generate_xml"
python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Boot_test --file_pattern 'test_boot.*' --config_file external/adt-infra/emu_test/config/boot_cfg_byob.csv --buildername $BUILDERNAME --filter '{"ori": "public"}' --generate_xml

#echo "Running Snapshot save/load tests"
#echo "Run python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Snapshot_test --file_pattern 'psq_test.*' --config_file external/adt-infra/emu_test/config/psq_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf"
#python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Snapshot_test --file_pattern 'psq_test.*' --config_file external/adt-infra/emu_test/config/psq_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf

echo "Remove any empty file"
find $SESSION_DIR -size  0 -print0 |xargs -0 rm --

# Check if boot test report generated
if [[ ! -f $SESSION_DIR/Boot_test/test_report.xml ]]
then
    exit 1
fi

# Check if boot test passed or failed
grep -q "failures=\"0\"" $SESSION_DIR/Boot_test/test_report.xml

exit $?
