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

TEST_DIR=$(dirname "$0")/..
AOSP_DIR=$(
    cd $TEST_DIR/../../..
    pwd
)

aosp_find_python() {
    local AOSP_PREBUILTS_DIR=$AOSP_DIR/prebuilts
    local OS_NAME=$(get_build_os)
    local PYTHON=$AOSP_PREBUILTS_DIR/python/$OS_NAME-x86/bin/python3
    $PYTHON --version >/dev/null || panic "Unable to get python version from $PYTHON"
    printf "$PYTHON"
}

PYTHON=$(aosp_find_python)
run $PYTHON $AOSP_DIR/external/adt-infra/pytest/test_embedded/run_tests.py --build_dir out/prebuilt_cached/builds --logdir $DISTRIB_DIR/testlogs