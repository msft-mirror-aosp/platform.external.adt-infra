#!/bin/bash
# Copyright 2022 The Android Open Source Project
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


# This is the build launcher script that is invoked by the automated build system
# The build system will provide the following parameters:
#
# $1 - The directory where the build should take place, this does not persist
# $2 - The distribution directory, every file in this directory will persist and
#      be available as an artifact for future download
# $3 - The build id, with the format  BUILD_ID := P?(\d+), build ids with a P prefix
#      are presubmit builds.
# $4 - The number of CPU's to use for building, **DEPRECATED**
# $5 - Whether or not to build the "qtwebengine". The presence of this flag indicates
#      that this build should include features meant for public release
. $(dirname "$0")/common.sh

OUT_DIR=$1
DISTRIB_DIR=$2
export BID=$3
export CPU=$4
QTWEBENGINE_ARG=$5
TEST_DIR=$(dirname "$0")/..

# Get the absolute path to the AOSP ROOT
AOSP_DIR=$(cd $TEST_DIR/../../..; pwd)
# Use the hermetic python interpreter and launch the build
PYTHON=$(aosp_find_python)
$PYTHON $AOSP_DIR/tools/buildSrc/servers/build_tools.py --out_dir $OUT_DIR --dist_dir $DISTRIB_DIR --build-id $BID $QTWEBENGINE_ARG || panic "build failure"

