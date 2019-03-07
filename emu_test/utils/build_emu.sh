#!/bin/bash

# This is used to build and test emulator binaries.
# This will be invoked by aosp-emu-master-dev.

OUT_DIR=$1
DIST_DIR=$2
BID=$3
CPU=$4

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

echo "Build Emulator"
echo "tools/buildSrc/servers/build_tools.sh $OUT_DIR $DIST_DIR $BID $CPU"
tools/buildSrc/servers/build_tools.sh $OUT_DIR $DIST_DIR $BID $CPU

echo "Run unzip -o $DIST_DIR/sdk-repo-$OS-emulator-*.zip -d $SESSION_DIR/emu-master-dev"
unzip -o $DIST_DIR/sdk-repo-$OS-emulator-*.zip -d $SESSION_DIR/emu-master-dev

echo "Running Boot tests"
echo "Remove any existing AVDs"
echo "sudo rm -rf $ANDROID_AVD_HOME/*"
sudo rm -rf $ANDROID_AVD_HOME/*

echo "Run python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Boot_test --file_pattern 'test_boot.*' --config_file external/adt-infra/emu_test/config/boot_cfg_byob.csv --buildername $BUILDERNAME --filter '{"ori": "public"}' --generate_xml"
python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Boot_test --file_pattern 'test_boot.*' --config_file external/adt-infra/emu_test/config/boot_cfg_byob.csv --buildername $BUILDERNAME --filter '{"ori": "public"}' --generate_xml

echo "Running Snapshot save/load tests"
echo "Run python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Snapshot_test --file_pattern 'psq_test.*' --config_file external/adt-infra/emu_test/config/psq_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf"
python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Snapshot_test --file_pattern 'psq_test.*' --config_file external/adt-infra/emu_test/config/psq_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf

echo "Remove any empty file"
find $SESSION_DIR -size  0 -print0 |xargs -0 rm --

exit 0
