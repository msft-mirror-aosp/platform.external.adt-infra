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
TEST_DIR=$(dirname "$0")/..
AOSP_DIR=$(
    cd $TEST_DIR/../../..
    pwd
)
STATUS=0
SESSION_DIR=$DISTRIB_DIR/testlogs
BUILD_DIR="out/prebuilt_cached/builds"
EMULATOR_EXE=$SESSION_DIR/emu-master-dev/emulator/emulator
SDK_EMULATOR=$AOSP_DIR/prebuilts/android-emulator-build/system-images/$(get_build_os)
export ANDROID_HOME=$SDK_EMULATOR
export ANDROID_SDK_ROOT=$SDK_EMULATOR
export ANDROID_EMU_ENABLE_CRASH_REPORTING="NO"
export PATH=$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$PATH

PYTHON=$(aosp_find_python)
mkdir -p $ANDROID_AVD_HOME

if [ -z "ANDROID_AVD_HOME" ]; then
    export ANDROID_AVD_HOME=/tmp/android-test
fi

BUILDERNAME="Linux_gce"
OS=$(get_build_os)

# Make sure we remove adb when we are exiting.
# Note that the value of "$?" after the trap action
# completes shall be the value it had before trap was invoked.
trap "terminate_adb" EXIT QUIT INT HUP


# Sets DISPLAY environment variable to the first working X server
set_display_env() {
    [ -d "/tmp/.X11-unix" ] && [ ! -L "/tmp/.X11-unix" ] || panic "No X server running!"
    local CWD=$PWD
    cd /tmp/.X11-unix
    for x in X*; do
        export DISPLAY=":${x#X}"
        if xset q &>/dev/null; then
            log "Found X server at \$DISPLAY [$DISPLAY]"
            break
        fi
        log "No X server at \$DISPLAY [$DISPLAY]"
    done
    cd $CWD
}

# The emulator needs an X server to launch on linux
# setup screen tries to find an active X server, and sets the
# display environment variable, so we can actually use it.
# This will launch a vnc server if needed.
setup_screen() {
    local OS=$(get_build_os)
    if [[ $OS == "linux" ]]; then
        ps cax | grep vnc >/dev/null
        if [ $? -eq 1 ]; then
            log "Start VNC server"
            silent_run vncserver
        fi
        set_display_env
    fi
}

# Set up the sdk manager to point to the proper location.
setup_sdk() {
    log "Using ANDROID_SDK_ROOT=$ANDROID_SDK_ROOT with prepackaged SDK manager"
    # accept all the licenses and install platform tools, the emulator needs these..
    # Since we don't care about the texts we /dev/null the output.
    (yes | $ANDROID_SDK_ROOT/cmdline-tools/latest/bin/sdkmanager --licenses) >/dev/null
    silent_run $ANDROID_SDK_ROOT/cmdline-tools/latest/bin/sdkmanager "platform-tools" "platforms;android-33"
    silent_run sdkmanager --channel=3 --install emulator
}

deploy_emulator() {
    log "Deploying emulator to $SESSION_DIR/emu-master-dev"
    run mkdir -p $SESSION_DIR/emu-master-dev
    run unzip -o $BUILD_DIR/sdk-repo-*-emulator-[0-9]*.zip -d $SESSION_DIR/emu-master-dev || panic "Unable to unzip required files."
}

setup_sdk   # Make sure the sdk dependencies are there
setup_screen # Configure the screen
deploy_emulator # Make sure the emulator is deployed.

# Run the android-studio embedded emulator tests
run_test "Embedded tests" $AOSP_DIR/external/adt-infra/pytest/test_embedded/run_tests.sh --session_dir $SESSION_DIR --emulator $SESSION_DIR/emu-master-dev/emulator/emulator --warn $(is_presubmit $BID)

export ANDROID_EMU_ENABLE_CRASH_REPORTING="NO"

clean_avds
log "activate virtualenv"
activate_virtualenv $TEST_DIR/utils
log "deactivate virtualenv"
deactivate_virtualenv

log "Remove any empty file"
find $SESSION_DIR -size 0 -delete || log "No empty files were deleted."

exit $STATUS
