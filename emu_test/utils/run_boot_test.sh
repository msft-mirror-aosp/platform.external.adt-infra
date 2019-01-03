#!/bin/bash

# This is used to run system image UI tests.
# This will be invoked by system image source.
#  {src}/platform_testing/ui_test/run_ui_test.sh

DIST_DIR=$1
ORI=$2
API=$3

BUILDERNAME="Linux_gce"
if [[ $OSTYPE == *"darwin"* ]]
then
    BUILDERNAME="Mac"
fi

echo "Running BOOT test for $API"

SESSION_DIR=$DIST_DIR/testlogs
mkdir -p $SESSION_DIR

FILTER={\"ori\":\"$ORI\"}

echo "Run python -u $ADT_INFRA/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $ANDROID_SDK_ROOT/emulator/emulator --test_dir BOOT_test --file_pattern 'test_boot.*' --config_file $ADT_INFRA/emu_test/config/boot_cfg_gce.csv --buildername $BUILDERNAME --filter $FILTER --generate_xml"
python -u $ADT_INFRA/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --emulator $ANDROID_SDK_ROOT/emulator/emulator --test_dir BOOT_test --file_pattern 'test_boot.*' --config_file $ADT_INFRA/emu_test/config/boot_cfg_gce.csv --buildername $BUILDERNAME --filter $FILTER --generate_xml

echo "Boot test completed"
