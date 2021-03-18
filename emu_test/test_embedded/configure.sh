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
    echo "It will create a virtual environment in which embedded tests will be installed."
    echo "This is really only needed for development, us run_tests.sh if you wish to"
    echo "just run the tests."
    exit 33
fi

echo "Please be patient, this make take a while.."
PYTHON=python

if [ ! -f "./venv/bin/activate" ]; then
  # Prefer python3 if it is available.
  if  python3 --version &>/dev/null; then
     echo "Using python 3"
     PYTHON=python3
     $PYTHON -m venv venv
     [ -e ./venv/bin/pip ] && ./venv/bin/pip install --upgrade pip
     [ -e ./venv/bin/pip ] && ./venv/bin/pip install --upgrade setuptools
  else
    echo "Python 2 ----<< Deprecated! See: https://python3statement.org/. Not supported."
    exit 1
  fi
fi
if [ -e ./venv/bin/activate ]; then
   . ./venv/bin/activate
   make deps
   python3 setup.py develop
   pip install pytest-timeout
   pip install pytest-benchmark
   echo "Ready to run emu-embeded tests.!"
fi
