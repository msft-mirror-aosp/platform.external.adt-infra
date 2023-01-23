#!/bin/bash
# Copyright 2020 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This is used to run AVD and embedded tests.
# This will be invoked by aosp-emu-master-dev.
. $(dirname "$0")/common.sh
# Let's log a lot.
set_verbosity 2

DISTRIB_DIR=$1
[ ! -d "$DISTRIB_DIR" ] && panic "The variable DISTRIB_DIR points to [$DISTRIB_DIR], which does not exist"

SESSION_DIR=$DISTRIB_DIR/testlogs

TEST_DIR=$(dirname "$0")/..
AOSP_DIR=$(
    cd $TEST_DIR/../../..
    pwd
)

deploy_emulator() {
    [ -z "$SESSION_DIR" ] && panic "SESSION_DIR variable not set, refusing to deploy."

    # Deploys the emulator and sets the EMULATOR_EXE variable to point to the emulator binary
    # Thas was unzipped.
    local BUILD_DIR="out/prebuilt_cached/builds"

    log "Deploying emulator to $SESSION_DIR/emu-master-dev"
    run mkdir -p $SESSION_DIR/emu-master-dev
    run unzip -o $BUILD_DIR/sdk-repo-*-emulator-[0-9]*.zip -d $SESSION_DIR/emu-master-dev || panic "Unable to unzip required files."
    EMULATOR_EXE=$SESSION_DIR/emu-master-dev/emulator/emulator
}

cleanup_emulator() {
    [ -z "$SESSION_DIR" ] && panic "SESSION_DIR variable not set, refusing to clean."
    [ ! -d "$SESSION_DIR" ] && panic "Refusing to delete non-existent directory."

    log "Removing $SESSION_DIR/emu-master-dev"
    rm -rf $SESSION_DIR/emu-master-dev

    log "Remove any empty file under $SESSION_DIR"
    find $SESSION_DIR -size 0 -delete || log "No empty files were deleted."
}

deploy_emulator

# Run the tests, that STATUS variable will contain success/failure.
$AOSP_DIR/external/adt-infra/pytest/test_embedded/run_tests.sh --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --logdir $SESSION_DIR/testlogs

cleanup_emulator
exit 0
