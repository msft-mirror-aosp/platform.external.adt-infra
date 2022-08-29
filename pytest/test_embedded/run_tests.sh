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

# Upgrade this as soon as the build bots support python3.
. $(dirname "$0")/shell/utils/common.sh
trap "terminate_adb" EXIT QUIT INT HUP
SCRIPT_DIR=$(dirname "$0")
PYTHON=python3
TIMEOUT_CMD="timeout"
WARN=false
alias python=python3

PY_VER=$($PYTHON -c 'import sys; exit(1) if sys.version_info.major < 3 and sys.version_info.minor < 5 else exit(0)')
$PY_VER || panic "No python3, not running these tests."

if ! command -v $TIMEOUT_CMD &>/dev/null; then
   TIMEOUT_CMD="gtimeout"
fi

# Parse the arguments
EMULATOR=
SESSION=
while [[ $# -gt 0 ]]; do
    key="$1"

    case $key in
    -e | --emulator)
        # Use python as MacOs does not have "realpath"
        REALPATH=$(python3 -c "import os; print(os.path.realpath('$2'))")
        EMULATOR="$REALPATH"
        shift # arg
        shift # val
        ;;
    -s | --session_dir)
        # Use python as MacOs does not have "realpath"
        REALPATH=$(python3 -c "import os; print(os.path.realpath('$2'))")
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
    *)
        shift # ignore
        ;;
    esac
done

echo "Using ${SESSION} and ${EMULATOR}"

restart_adb() {
    echo "Stopping adb"
    terminate_adb
    ADB_TRACE=all
    echo "Starting adb"
    $ANDROID_SDK_ROOT/platform-tools/adb start-server
}

restart_adb

mkdir -p ${SESSION}/embedded_test/log/

python3 -m venv /tmp/venv
source /tmp/venv/bin/activate

export PATH=$PATH:$HOME/.local/bin
# Now actually run the tests, note we have to redirect stderr to
# stdout for the build bots, and we don't want to run longer than 5 mins.
${TIMEOUT_CMD} 600 make -C ${SCRIPT_DIR} check EMULATOR=${EMULATOR} SESSION_DIR=${SESSION} 1>&2
status=$?

if [ $status -ne 0 ]; then
    echo "============ FAILURE LOG ==============="
    cat ${SESSION}/embedded_test/log/pytest.log
    echo "============ FAILURE LOG ==============="
fi

# Forcefully terminate adb, as the build bots will hang otherwise.
terminate_adb

# Only propagate errors if --warn true has been requested.
case "$WARN" in
    *true* ) exit $status;;
    * ) exit 0;;
esac
