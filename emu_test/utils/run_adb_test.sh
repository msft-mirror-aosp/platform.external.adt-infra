#!/bin/bash
#
# run_adb_test.sh
#
# Run adb embedded tests
#
# Copyright 2023 The Android Open Source Project
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
#
# Arguments:
#
#  $1 DISTRIB_DIR

# We do our own error handling
set +e
DISTRIB_DIR=$1

VERBOSE=3
. $(dirname "$0")/common.sh

set_verbosity 3
[ ! -d "$DISTRIB_DIR" ] && panic "The variable DISTRIB_DIR points to [$DISTRIB_DIR], which does not exist"

AOSP_DIR=$(
    cd $(dirname $0)/../../../..
    pwd
)

build_target=${BUILD_TARGET_NAME:-unknown_build_target}

# Finds the python installation that is part of our repository
aosp_find_python() {
    local AOSP_PREBUILTS_DIR=$AOSP_DIR/prebuilts
    local OS_NAME=$(get_build_os)
    local PYTHON=$AOSP_PREBUILTS_DIR/python/$OS_NAME-x86/bin/python3
    $PYTHON --version >/dev/null || panic "Unable to get python version from $PYTHON"
    printf "$PYTHON"
}

check_physical_display
PYTHON=$(aosp_find_python)
export PYTEST_ADDOPTS="-m 'adb'"
run $PYTHON "$AOSP_DIR/external/adt-infra/pytest/test_embedded/run_tests.py" --build_dir out/prebuilt_cached/builds --logdir "$DISTRIB_DIR/testlogs" --build_target $build_target
