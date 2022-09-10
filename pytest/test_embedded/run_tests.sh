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
trap "terminate_adb" EXIT QUIT INT HUP

_SHU_VERBOSE=3
AOSP_DIR=$(
  cd $(dirname $0)/../../../..
  pwd
)

aosp_find_python() {
    local AOSP_PREBUILTS_DIR=$AOSP_DIR/prebuilts
    local OS_NAME=$(get_build_os)
    local PYTHON=$AOSP_PREBUILTS_DIR/python/$OS_NAME-x86/bin/python3
    $PYTHON --version >/dev/null || panic "Unable to get python version from $PYTHON"
    printf "$PYTHON"
}

write_local_pip_conf() {
    cp $HERE/cfg/pip.conf $VIRTUAL_ENV/pip.conf
    cp $HERE/cfg/pypirc $VIRTUAL_ENV/pypirc
}

# Launches a devpi server, this server should be launched using the default
# python interpreter that has access to the official pypi server, so missing
# packages can be retrieved.
launch_devpi() {
    # Get the absolute directory where we can find devpi.
    DEVPI_DIR=$(
        cd $AOSP_DIR/external/adt-infra/devpi
        pwd
    )

    if [ ! -z "$GENERATE" ]; then
        # Note: we only use this to pick up the missing packages (if any)
        # once we have done this, it can be removed.
        run cp -r $DEVPI_DIR $SESSION
        DEVPI_DIR=$(
            cd $SESSION/devpi
            pwd
        )
    fi
    log "Using $DEVPI_DIR"

    SERVERDIR=$DEVPI_DIR/server
    run pip3 install devpi-server devpi-client # --index-url $DEVPI_DIR/repo/simple
    run devpi-init --serverdir $SERVERDIR --root-passwd "@verys@f3pa@ssw0rd"
    run devpi-server --serverdir $SERVERDIR &
    DEVPI_PID=$!
    let NEXT_WAIT_TIME=0
    while [ $NEXT_WAIT_TIME -ne 5 ]; do
        if nc -z localhost 3141; then break; fi
        ((NEXT_WAIT_TIME=NEXT_WAIT_TIME+1))
        echo "Waiting for devpi"
        sleep 1
    done

    run devpi use http://localhost:3141
    run devpi login root --password "@verys@f3pa@ssw0rd"
    run devpi user -c packages email=adt-infra@google.com password=packages
    run devpi index -c packages/stable bases=root/pypi volatile=False
    run devpi index -c packages/staging bases=packages/stable volatile=True
}

terminate_devpi() {
    # Terminates any running instance of adb if one exists.
    log "Terminating adb"
    kill -9 $DEVPI_PID
    _procs=$(ps -A | grep devpi | awk '{ print $1; }')
    for _proc in $_procs; do
        run kill -9 $_proc
    done
}

trap "terminate_devpi" EXIT QUIT INT HUP

# Parse the arguments, and get going..
EMULATOR=$ANDROID_SDK_ROOT/emulator/emulator
SESSION=session_dir
while [[ $# -gt 0 ]]; do
    key="$1"

    case $key in
    -e | --emulator)
        # Use python as MacOs does not have "realpath"
        REALPATH=$(
            cd $(dirname $2)
            echo $PWD/$(basename $2)
        )
        EMULATOR="$REALPATH"
        shift # arg
        shift # val
        ;;
    -s | --session_dir)
        # Use python as MacOs does not have "realpath"
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

AEMU_GRPC=$AOSP_DIR/external/qemu/android/android-grpc/python/aemu-grpc/
SNAPTOOL=$AOSP_DIR/external/qemu/android/android-grpc/python/snaptool/
PYTHON=$(aosp_find_python)
HERE=$AOSP_DIR/external/adt-infra/pytest/test_embedded
PY_VER=$($PYTHON --version)
PATH=$HOME/.local/bin:$PATH
VIRTUAL_ENV_DEST=$(mktemp -d -t e2e-tests-XXXXXXXX)

launch_devpi # Note devpi is running under the default interpreter

run $PYTHON -m venv $VIRTUAL_ENV_DEST

if [ -e $VIRTUAL_ENV_DEST/bin/activate ]; then
    . $VIRTUAL_ENV_DEST/bin/activate
    write_local_pip_conf
    run pip install --upgrade pip wheel setuptools
fi

restart_adb() {
    echo "Stopping adb"
    terminate_adb
    ADB_TRACE=all
    echo "Starting adb"
    $ANDROID_SDK_ROOT/platform-tools/adb start-server
}

make_wheel() {
    mkdir -p $SESSION/dist
    CFLAGS='-w' pip wheel $1 -w $SESSION/dist
    run twine upload -r devpi-staging --config-file  $VIRTUAL_ENV/pypirc $SESSION/dist/*
}

rm -rf $SESSION/dist
run pip install twine
make_wheel $AEMU_GRPC
make_wheel $SNAPTOOL
run pip install tox tox-venv
run pip install -e .\[test\]

if [ ! -z "$GENERATE" ]; then
    # Get all the dependencies..
    run pip download devpi-server -d $SESSION/dist
fi

restart_adb
(
    cd $HERE
    tox --workdir ${SESSION}/embedded_test -- -x --emulator=${EMULATOR}
)

STATUS=$?
if [ $STATUS -ne 0 ]; then
    echo "============ FAILURE LOG ==============="
    cat ${SESSION}/embedded_test/log/pytest.log
    echo "============ FAILURE LOG ==============="
fi


# Only propagate errors if --warn true has been requested.
case "$WARN" in
*true*) exit $STATUS ;;
*) exit 0 ;;
esac
