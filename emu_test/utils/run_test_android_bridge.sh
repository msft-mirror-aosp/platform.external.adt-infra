#!/bin/bash

# This is used to run ADB tests.
# This will be invoked by devtools-test branch source.
# {src}/test/run_android_bridge_test.sh

set -x
echo $@
env

. $(dirname "$0")/common.sh

DISTRIB_DIR=$1
ADB_EXEC=$2
SERIAL=$3

export ANDROID_SERIAL=$SERIAL

BUILDERNAME="Linux"
if [[ $OSTYPE == *"darwin"* ]]
then
    BUILDERNAME="Mac"
fi

SESSION_DIR=$DISTRIB_DIR/testlogs
mkdir -p $SESSION_DIR

log "activate virtualenv"
activate_virtualenv

python3 -u $ADT_INFRA/emu_test/dotest.py --loglevel DEBUG --session_dir $SESSION_DIR --test_dir ADB_test --file_pattern 'test_adb.*' --use_device --adb $ADB_EXEC

log "deactivate virtualenv"
deactivate_virtualenv

find $SESSION_DIR -size  0 -print0 |xargs -0 rm --

echo "ADB test completed"
