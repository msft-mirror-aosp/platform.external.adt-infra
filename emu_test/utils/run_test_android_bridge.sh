#!/bin/bash

# This is used to run ADB tests.
# This will be invoked by devtools-test branch source.
# {src}/test/run_android_bridge_test.sh

set -x
echo $@
env

DISTRIB_DIR=$1
FILTER=$2

export PATH=$PATH:$ANDROID_SDK_ROOT/platform-tools

echo "using ADB"
which adb

BUILDERNAME="Linux"
if [[ $OSTYPE == *"darwin"* ]]
then
    BUILDERNAME="Mac"
fi

SESSION_DIR=$DISTRIB_DIR/testlogs
mkdir -p $SESSION_DIR

python -u $ADT_INFRA/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --test_dir ADB_test --file_pattern 'test_adb.*' --config_file $ADT_INFRA/emu_test/config/adb_cfg_byob.csv --buildername $BUILDERNAME --filter $FILTER --use_device

find $SESSION_DIR -size  0 -print0 |xargs -0 rm --

echo "ADB test completed"
