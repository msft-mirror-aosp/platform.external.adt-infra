#!/bin/bash

# This is used to run system image UI tests.
# This will be invoked by system image source.
#  {src}/platform_testing/ui_test/run_ui_test.sh

DIST_DIR=$1
ORI=$2
API=$3

echo "Running UI test for $API"

for FILE in "$ANDROID_HOME/system-images/android-$API"/*
do
    FILENAME=$(basename $FILE)
    if [[ $FILENAME == *"tv"* ]]
    then
        TARGET=tv
        FILTER={\"tag\":\"android-tv\",\"ori\":\"$ORI\"}
    elif [[ $FILENAME == *"wear"* ]]
    then
        TARGET=wear
        FILTER={\"tag\":\"android-wear\",\"ori\":\"$ORI\"}
    elif [[ $FILENAME == *"playstore"* ]]
    then
        TARGET=gphone-user
        FILTER={\"tag\":\"google_apis_playstore\",\"ori\":\"$ORI\"}
    else
        continue
    fi

    SESSION_DIR=$DIST_DIR/gtest
    TEST_DIR=UI_TEST_$TARGET
    mkdir -p $SESSION_DIR

    echo "Run test for $TARGET"
    echo "Run python -u $ADT_INFRA/emu_test/dotest.py --loglevel INFO --session_dir $SESSION_DIR --emulator $ANDROID_SDK_ROOT/emulator/emulator --test_dir $TEST_DIR --file_pattern 'test_ui.*' --config_file $ADT_INFRA/emu_test/config/ui_cfg_gce.csv --buildername 'Ubuntu 14.04 HD 4400' --filter $FILTER --skip-adb-perf"
    python -u $ADT_INFRA/emu_test/dotest.py --loglevel INFO --session_dir $SESSION_DIR --emulator $ANDROID_SDK_ROOT/emulator/emulator --test_dir $TEST_DIR --file_pattern 'test_ui.*' --config_file $ADT_INFRA/emu_test/config/ui_cfg_gce.csv --buildername 'Ubuntu 14.04 HD 4400' --filter $FILTER --skip-adb-perf

done
