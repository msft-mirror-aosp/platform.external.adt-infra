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

# We do our own error handling
set +e
. $(dirname "$0")/shell/utils/common.sh

# Make sure we stop adb, and exit our virtual env.
trap "terminate_adb" EXIT QUIT INT HUP

_SHU_VERBOSE=3
AOSP_DIR=$(
    cd $(dirname $0)/../../../..
    pwd
)

# Finds the python installation that is part of our repository
aosp_find_python() {
    local AOSP_PREBUILTS_DIR=$AOSP_DIR/prebuilts
    local OS_NAME=$(get_build_os)
    local PYTHON=$AOSP_PREBUILTS_DIR/python/$OS_NAME-x86/bin/python3
    $PYTHON --version >/dev/null || panic "Unable to get python version from $PYTHON"
    printf "$PYTHON"
}

# Finds the python include header path that is part of our repository
aosp_find_python_include() {
    local AOSP_PREBUILTS_DIR=$AOSP_DIR/prebuilts
    local OS_NAME=$(get_build_os)
    local PYTHON_H=$(find $AOSP_PREBUILTS_DIR/python/$OS_NAME-x86/include -name 'Python.h')
    local PYTHON_INCLUDE=$(dirname $PYTHON_H)
    printf "$PYTHON_INCLUDE"
}

# Returns true if there is something running on port 3141 (We expect devpi here)
is_devpi_running() {
    nc -z localhost 3141
}

# Retrieves the devpi dir, the location where all the wheels and eggs can be found
devpi_dir() {
    DEVPI_DIR=$(
        cd $AOSP_DIR/external/adt-infra/devpi
        pwd
    )

    if [ ! -z "$GENERATE" ]; then
        # Note: we only use this to pick up the missing packages (if any)
        # once we have done this, it can be removed.
        cp -r $DEVPI_DIR $SESSION
        DEVPI_DIR=$(
            cd $SESSION/devpi
            pwd
        )
    fi
    printf "$DEVPI_DIR"
}

# Launches a devpi server, this server should be launched using the default
# python interpreter that has access to the official pypi server, so missing
# packages can be retrieved if needed.
launch_devpi() {
    # Get the absolute directory where we can find devpi.
    DEVPI_DIR=$(devpi_dir)
    log "Using $DEVPI_DIR"

    SERVERDIR=$DEVPI_DIR/server
    run pip3 install -q -U --upgrade devpi-server devpi-client --index-url file://$DEVPI_DIR/repo/simple

    # Only really needed on first run..
    run devpi-init --serverdir $SERVERDIR --root-passwd "@verys@f3pa@ssw0rd"

    # You will get a lot of spam if this is not silent.
    silent_run devpi-server --serverdir $SERVERDIR &
    DEVPI_PID=$!

    # Wait until devpi is accessible.
    let NEXT_WAIT_TIME=0
    while [ $NEXT_WAIT_TIME -ne 5 ]; do
        if is_devpi_running; then break; fi
        ((NEXT_WAIT_TIME = NEXT_WAIT_TIME + 1))
        log2 "Waiting for devpi"
        sleep 1
    done

    # And configure it for usage
    silent_run devpi use http://localhost:3141
    silent_run devpi login root --password "@verys@f3pa@ssw0rd"
}

# Terminates any running instance of devpi if one exists.
terminate_devpi() {
    terminate_proc_by_name devpi
}

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
    OS=$(get_build_os)
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
}

# Setup a python virtual env with proper paths and links
setup_virtual_env() {
    # We need a virtual environment, so we can set up the proper include directories
    # as, well, it seem that our crippled python release does not report the proper include
    # directory
    local PYTHON=$(aosp_find_python)
    local PYTHON_INCLUDE=$(aosp_find_python_include)
    local VIRTUAL_ENV_DEST=$(mktemp -d -t e2e-testsp-XXXXXX)
    local WHEEL_DIR=$(devpi_dir)/repo/simple

    run $PYTHON -m venv $VIRTUAL_ENV_DEST
    rm -r $VIRTUAL_ENV_DEST/include
    ln -sf $PYTHON_INCLUDE $VIRTUAL_ENV_DEST/include

    # Activate and setup a pip conf that points to our local devpi server
    # This will make sure all our packages are from the local server.
    . $VIRTUAL_ENV_DEST/bin/activate

    # Fix up our pip to point to local file system
    cat $HERE/cfg/pip.conf | sed "s,REPO_DIR,$WHEEL_DIR,g" >$VIRTUAL_ENV_DEST/pip.conf
    cp $HERE/cfg/pypirc $VIRTUAL_ENV_DEST/pypirc
    silent_run pip install --upgrade pip wheel setuptools
}

# Restarts adb
restart_adb() {
    terminate_adb
    ADB_TRACE=all
    run $ANDROID_SDK_ROOT/platform-tools/adb start-server
}

# Parse the arguments, and get going..
EMULATOR=$ANDROID_SDK_ROOT/emulator/emulator
SESSION=$PWD/session_dir
while [[ $# -gt 0 ]]; do
    key="$1"

    case $key in
    -e | --emulator)
        REALPATH=$(
            cd $(dirname $2)
            echo $PWD/$(basename $2)
        )
        EMULATOR="$REALPATH"
        shift # arg
        shift # val
        ;;
    -s | --session_dir)
        REALPATH=$(
            cd $2
            pwd
        )
        SESSION="$REALPATH"
        shift # arg
        shift # val
        ;;
    -w | --warn)
        WARN=$2
        echo "Treat failures/warnings as errors? $WARN"
        shift
        shift
        ;;
    -g | --generate)
        GENERATE=True
        echo "Generating wheel dependencies in $SESSION"
        shift
        ;;
    *)
        shift # ignore
        ;;
    esac
done

echo "Session: ${SESSION} and Emulator: ${EMULATOR}, AOSP: $AOSP_DIR"
SDK_EMULATOR=$AOSP_DIR/prebuilts/android-emulator-build/system-images/$(get_build_os)
export ANDROID_HOME=$SDK_EMULATOR
export ANDROID_SDK_ROOT=$SDK_EMULATOR
export ANDROID_EMU_ENABLE_CRASH_REPORTING="NO"

AEMU_GRPC=$AOSP_DIR/external/qemu/android/android-grpc/python/aemu-grpc/
SNAPTOOL=$AOSP_DIR/external/qemu/android/android-grpc/python/snaptool/
HERE=$AOSP_DIR/external/adt-infra/pytest/test_embedded
PATH=$HOME/.local/bin:$PATH:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$PATH
ANDROID_AVD_HOME=$(mktemp -d -t avd-home-XXXXXXX)

# When generating files we need a local devpi server
if [ ! -z "$GENERATE" ]; then
    if is_devpi_running; then
        log "Using existing devpi server."
    else
        launch_devpi # Note devpi is running under the default interpreter
        trap "terminate_devpi" EXIT QUIT INT HUP
    fi
fi

setup_screen      # Make sure we have a working display environment
setup_sdk         # Make sure android emulato dependencies are present
setup_virtual_env # Start a virtual environment

#clean out dangling pyc files.
find $HERE -name '*.pyc' -delete
find $VIRTUAL_ENV -name '*.pyc' -delete

if [ ! -z "$GENERATE" ]; then
    # Get all the dependencies, compile them, and place them in the dist dir
    rm -rf $SESSION/dist
    run pip wheel --no-cache --wheel-dir=$SESSION/dist $AEMU_GRPC $SNAPTOOL $HERE
fi

run pip install --upgrade --force-reinstall $AEMU_GRPC $SNAPTOOL
run pip install --upgrade --force-reinstall -e $HERE\[test\]

mkdir -p $SESSION/embedded_test
restart_adb


# We are going to create a temporary report, that we will spruce up
TMP_TEST_RESULT=$VIRTUAL_ENV/test_unit.xml
FINAL_RESULT=$SESSION/embedded_test/test_embedded_test.xml

# Now let's run pytests
(
    cd $HERE
    pytest -vv -m "not perf" --junitxml=$TMP_TEST_RESULT --timeout=600 --log-file=$SESSION/embedded_test/log/pytest.log
)
STATUS=$?

# If a junit report was created we will:
# - Produce a readable html file, this can be used to diagnose a test failure
# - Make a sponge compatible report that only includes output for failures.
if [ -f $TMP_TEST_RESULT ]; then
    python $HERE/src/xml/transform.py --xml $TMP_TEST_RESULT --xsl $HERE/cfg/asHtml.xslt --out $SESSION/test_report.html

    # Next we lift out the failure messages, this makes it WAAAYYY easier to debug things in sponge..
    python $HERE/src/xml/transform.py --xml $TMP_TEST_RESULT --xsl $HERE/cfg/liftSystemOut.xslt --out $FINAL_RESULT
    if [ $STATUS -ne 0 ]; then
        warn "== TEST FAILURES! Check $SESSION/test_report.html for details on which test failed."
    fi
else
    warn "============ PYTEST NO JUNIT TEST RESULT WAS PRODUCED ==============="
    cat ${SESSION}/embedded_test/log/pytest.log >&2
fi

# Clean up unused extra data
run rm -rf ${SESSION}/embedded_test/py3 ${SESSION}/embedded_test/dist $VIRTUAL_ENV

# Only propagate errors if --warn true has been requested.
case "$WARN" in
*true*) exit $STATUS ;;
*) exit 0 ;;
esac
