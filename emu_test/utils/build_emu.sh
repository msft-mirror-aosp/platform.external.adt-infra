#!/bin/bash

# This is used to build and test emulator binaries.
# This will be invoked by aosp-emu-master-dev.
. $(dirname "$0")/common.sh

OUT_DIR=$1
DISTRIB_DIR=$2
export BID=$3
export CPU=$4
USE_QTWEBENGINE=$5

TEST_DIR=$(dirname "$0")/..

# Let's log the commands.
set_verbosity 2

# Make sure all the expected variables have been set.
check_vars ANDROID_AVD_HOME SDK_EMULATOR  DISTRIB_DIR

export ANDROID_HOME=$SDK_EMULATOR
export ANDROID_SDK_ROOT=$SDK_EMULATOR
export ANDROID_EMU_ENABLE_CRASH_REPORTING="NO"

# Make sure we remove adb when we are exiting.
# Note that the value of "$?" after the trap action
# completes shall be the value it had before trap was invoked.
trap "terminate_adb" EXIT QUIT INT HUP

PYTHON=python

# Prefer python3 if it is available.
if command -v python3 &>/dev/null; then
  log "Using python 3"
  PYTHON=python3
  $PYTHON -m venv $OUT_DIR/venv
  [ -e $OUT_DIR/venv/bin/pip ] && $OUT_DIR/venv/bin/pip install --upgrade pip setuptools requests
else
  log "Using python 2.. This is no longer officially supported!"
  log "https://python3statement.org/"
fi

QTWEBENGINE_ARG=
if [[ $USE_QTWEBENGINE == "qtwebengine" ]]; then
    QTWEBENGINE_ARG="--qtwebengine"
fi

$PYTHON tools/buildSrc/servers/build_tools.py --out_dir $OUT_DIR --dist_dir $DISTRIB_DIR --build-id $BID $QTWEBENGINE_ARG || panic "build failure"

