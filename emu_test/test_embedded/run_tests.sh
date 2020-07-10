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
SCRIPT_DIR=$(dirname "$0")
VENV_DIR=${SESSION_DIR:-$SCRIPT_DIR}/venv
PYTHON=python2
TIMEOUT_CMD="timeout"


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
        REALPATH=$(python -c "import os; print(os.path.realpath('$2'))")
        EMULATOR="EMULATOR=$REALPATH"
        shift # arg
        shift # val
        ;;
    -s | --session_dir)
        # Use python as MacOs does not have "realpath"
        REALPATH=$(python -c "import os; print(os.path.realpath('$2'))")
        SESSION="SESSION_DIR=$REALPATH"
        shift # arg
        shift # val
        ;;
    *)
        shift # ignore
        ;;
    esac
done

echo "Using ${SESSION} and ${EMULATOR}"

setup_virtual_env() {

    ${PYTHON} -m pip &>/dev/null || ${PYTHON} -m easy_install --user pip==19.3.1
    # First make sure we have the proper setuptools available.
    # The bots are running very old versions of everything, so we have to separate
    # all of these!
    pip install -q --user setuptools

    # Make sure virtualenv is available and activate it
    pip install -q --user virtualenv

    ${PYTHON} -m virtualenv ${VENV_DIR}
    source ${VENV_DIR}/bin/activate
}

setup_virtual_env

# Now actually run the tests, note we have to redirect stderr to
# stdout for the build bots, and we don't want to run longer than 5 mins.
${TIMEOUT_CMD} 300 make -C ${SCRIPT_DIR} check ${EMULATOR} ${SESSION} 1>&2
status=$?

# Forcefully terminate adb, as the build bots will hang otherwise.
ps -A | grep adb | awk '{ print $1; }' | xargs kill -9 || true

exit $status