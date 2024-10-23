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

function check_no_aosp_flag() {
  for flag in "$@"; do
    if [[ "$flag" == "--no-aosp" ]]; then
      return 0
    fi
  done
  return 1
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

aosp_find_python_include() {
    local AOSP_PREBUILTS_DIR=$AOSP_DIR/prebuilts
    local OS_NAME=$(get_build_os)
    local PYTHON_H=$(find $AOSP_PREBUILTS_DIR/python/$OS_NAME-x86/include -name 'Python.h')
    local PYTHON_INCLUDE=$(dirname $PYTHON_H)
    printf "$PYTHON_INCLUDE"
}

write_local_pip_conf() {
  cp ./cfg/pip.conf $VIRTUAL_ENV/pip.conf
  cp ./cfg/pypirc $VIRTUAL_ENV/pypirc
}

AOSP_DIR=$(
  cd ../../../..
  pwd
)

HERE=$AOSP_DIR/external/adt-infra/pytest/test_embedded
AEMU_GRPC=$AOSP_DIR/external/qemu/android/android-grpc/python/aemu-grpc/
SNAPTOOL=$AOSP_DIR/external/qemu/android/android-grpc/python/snaptool/
NETSIM_GRPC=$AOSP_DIR/tools/netsim/testing/netsim-grpc/

# Point ANDROID_SDK_ROOT to the one that we ship
SDK_EMULATOR=$AOSP_DIR/prebuilts/android-emulator-build/system-images/$(get_build_os)
export ANDROID_HOME=$SDK_EMULATOR
export ANDROID_SDK_ROOT=$SDK_EMULATOR

devpi_dir() {
    DEVPI_DIR=$(
        cd $AOSP_DIR/external/adt-infra/devpi
        pwd
    )
    printf "$DEVPI_DIR"
}

setup_virtual_env() {
    # We need a virtual environment, so we can set up the proper include directories
    # as, well, it seem that our crippled python release does not report the proper include
    # directory
    if check_no_aosp_flag "$@"; then
       echo "Using local python interpreter"
       local PYTHON=python3
       $PYTHON -m venv $VIRTUAL_ENV_DEST
    else
      local PYTHON=$(aosp_find_python)
      local PYTHON_INCLUDE=$(aosp_find_python_include)
      $PYTHON -m venv $VIRTUAL_ENV_DEST

      rm -r $VIRTUAL_ENV_DEST/include
      ln -sf $PYTHON_INCLUDE $VIRTUAL_ENV_DEST/include
    fi
    local WHEEL_DIR=$(devpi_dir)/repo/simple

    # Activate and setup a pip conf that points to our local devpi server
    # This will make sure all our packages are from the local server.
    . $VIRTUAL_ENV_DEST/bin/activate

    # Fix up our pip to point to local file system
    cat $HERE/cfg/pip.conf | sed "s,REPO_DIR,$WHEEL_DIR,g" >$VIRTUAL_ENV_DEST/pip.conf
    cp $HERE/cfg/pypirc $VIRTUAL_ENV_DEST/pypirc
    pip install --upgrade pip wheel setuptools
    pip install wheel $AEMU_GRPC $SNAPTOOL $NETSIM_GRPC
}
echo "Make sure you have the devpi server up and running!"

VIRTUAL_ENV_DEST=./.venv
if [ -e $VIRTUAL_ENV_DEST/bin/activate ]; then
  . $VIRTUAL_ENV_DEST/bin/activate
else
  setup_virtual_env "$@"
fi
