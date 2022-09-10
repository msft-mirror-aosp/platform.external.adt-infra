#!/bin/sh
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
if [ "${BASH_SOURCE-}" = "$0" ]; then
  echo "You must source this script: \$ source $0" >&2
  echo "It will create a virtual environment in which emu-docker will be installed."
  exit 33
fi

panic() {
  echo "ERROR: $@" >&2
  exit 1
}

# Return the build machine's operating system tag.
# Valid return values are:
#    linux
#    darwin
#    freebsd
#    windows   (really MSys)
#    cygwin
get_build_os() {
  if [ -z "$_SHU_BUILD_OS" ]; then
    _SHU_BUILD_OS=$(uname -s)
    case $_SHU_BUILD_OS in
    Darwin)
      _SHU_BUILD_OS=darwin
      ;;
    FreeBSD) # note: this is not tested
      _SHU_BUILD_OS=freebsd
      ;;
    Linux)
      # note that building  32-bit binaries on x86_64 is handled later
      _SHU_BUILD_OS=linux
      ;;
    CYGWIN* | *_NT-*)
      _SHU_BUILD_OS=windows
      if [ "x$OSTYPE" = xcygwin ]; then
        _SHU_BUILD_OS=cygwin
      fi
      ;;
    esac
  fi
  echo "$_SHU_BUILD_OS"
}

aosp_find_python() {
  local AOSP_PREBUILTS_DIR=$AOSP_DIR/prebuilts
  local OS_NAME=$(get_build_os)
  local PYTHON=$AOSP_PREBUILTS_DIR/python/$OS_NAME-x86/bin/python3
  $PYTHON --version >/dev/null || panic "Unable to get python version from $PYTHON"
  printf "$PYTHON"
}

write_local_pip_conf() {
  cp ./cfg/pip.conf $VIRTUAL_ENV/pip.conf
  cp ./cfg/pypirc $VIRTUAL_ENV/pypirc
}

AOSP_DIR=$(
  cd ../../../..
  pwd
)
AEMU_GRPC=$AOSP_DIR/external/qemu/android/android-grpc/python/aemu-grpc/
SNAPTOOL=$AOSP_DIR/external/qemu/android/android-grpc/python/snaptool/
PYTHON=$(aosp_find_python)
PY_VER=$($PYTHON --version)

$PYTHON -m venv .venv
write_local_pip_conf

echo "Make sure you have the devpi server up and running!"

if [ -e ./.venv/bin/activate ]; then
  . ./.venv/bin/activate
  pip install wheel $AEMU_GRPC $SNAPTOOL
  pip install -e .
fi
