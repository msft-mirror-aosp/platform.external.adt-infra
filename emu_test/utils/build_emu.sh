#!/bin/bash

# This is used to build and test emulator binaries.
# This will be invoked by aosp-emu-master-dev.

OUT_DIR=$1
DISTRIB_DIR=$2
BID=$3
CPU=$4
USE_QTWEBENGINE=$5

panic() {
  # Display a message and exit
   printf "%s\n" "$*" >&2
   exit 1
}

# Prevent users from accidentally nuking their machine..
# As sudo rm -rf / will destroy your machine, just like it did mine.
[[ -z ${ANDROID_AVD_HOME} ]] &&  panic "ANDROID_AVD_HOME is unset"
[[ -z ${SDK_EMULATOR} ]] && panic "SDK_EMULATOR is unset, it should point to something like ANDROID_SDK_ROOT"
[[ -z ${DISTRIB_DIR} ]] && panic "No distribution directory provided!"


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

QTWEBENGINE_ARG=
if [[ $USE_QTWEBENGINE == "qtwebengine" ]]; then
    QTWEBENGINE_ARG="--qtwebengine"
fi
echo "tools/buildSrc/servers/build_tools.py --out_dir $OUT_DIR --dist_dir $DISTRIB_DIR --build-id $BID $QTWEBENGINE_ARG"
tools/buildSrc/servers/build_tools.py --out_dir $OUT_DIR --dist_dir $DISTRIB_DIR --build-id $BID $QTWEBENGINE_ARG

if [[ $? -ne 0 ]]
then
  panic "build failure"
fi

echo "Run unzip -o $DISTRIB_DIR/sdk-repo-$OS-emulator-[P,0-9]*.zip -d $SESSION_DIR/emu-master-dev"
unzip -o $DISTRIB_DIR/sdk-repo-$OS-emulator-[P,0-9]*.zip -d $SESSION_DIR/emu-master-dev

# Contains all the unit tests, symbols, debug_information and testing tools needed for some e2e tests.
echo "Run unzip -o $DISTRIB_DIR/sdk-repo-$OS-debug-emulator-[P,0-9]*.zip -d $SESSION_DIR/emu-master-dev-dbg"
unzip -o $DISTRIB_DIR/sdk-repo-$OS-debug-emulator-[P,0-9]*.zip -d $SESSION_DIR/emu-master-dev-dbg

echo "Running Boot tests"
echo "Remove any existing AVDs"
echo "rm -rf $ANDROID_AVD_HOME/*"
rm -rf $ANDROID_AVD_HOME/*

echo "Run python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Boot_test --file_pattern 'test_boot.*' --config_file external/adt-infra/emu_test/config/boot_cfg_byob.csv --buildername $BUILDERNAME --filter '{"ori": "public"}' --generate_xml"
python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Boot_test --file_pattern 'test_boot.*' --config_file external/adt-infra/emu_test/config/boot_cfg_byob.csv --buildername $BUILDERNAME --filter '{"ori": "public"}' --generate_xml

export ANDROID_EMU_ENABLE_CRASH_REPORTING="YES"
echo "Running Crash tests"
echo "Run python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Crash_test --file_pattern 'test_crash.*' --config_file external/adt-infra/emu_test/config/crash_cfg_byob.csv --buildername $BUILDERNAME  --generate_xml --skip-adb-perf"
python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Crash_test --file_pattern 'test_crash.*' --config_file external/adt-infra/emu_test/config/crash_cfg_byob.csv --buildername $BUILDERNAME  --generate_xml --skip-adb-perf
export ANDROID_EMU_ENABLE_CRASH_REPORTING="NO"

#echo "Running Snapshot save/load tests"
#echo "Run python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Snapshot_test --file_pattern 'psq_test.*' --config_file external/adt-infra/emu_test/config/psq_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf"
#python -u external/adt-infra/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --test_dir Snapshot_test --file_pattern 'psq_test.*' --config_file external/adt-infra/emu_test/config/psq_cfg_byob.csv --buildername $BUILDERNAME --skip-adb-perf

echo "Remove any empty file"
$(find $SESSION_DIR -size  0 -print0) | xargs -0 rm --

# Check if test reports were generated.
[[ ! -f $SESSION_DIR/Boot_test/test_report.xml ]] && panic "No boot test report found"
[[ ! -f $SESSION_DIR/Crash_test/test_report.xml ]] && panic "No crash test report found"


# Check if boot & crash test passed or failed
grep -q "failures=\"0\"" $SESSION_DIR/Boot_test/test_report.xml || panic "Failures in boot test"
grep -q "failures=\"0\"" $SESSION_DIR/Crash_test/test_report.xml || panic "Failures in crash test"
echo "Success!"
