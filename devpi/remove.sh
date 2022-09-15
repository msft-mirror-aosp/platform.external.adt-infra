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

# Upload a new package to the devpi server and check it into git
HERE=$(cd $(dirname $0); pwd)

if ! command -v symlinks  &> /dev/null
then
    echo "Please intall https://github.com/brandt/symlinks.git (apt install symlinks)"
    exit 1
fi

if ! nc -z localhost 3141; then
    echo "It doesn't look like devpi is running, make sure to call ./launch-devpi.sh in a different shell"
    exit 1
fi

# Setup twine and devpi.
pip install devpi-client twine pip2pi
devpi use http://localhost:3141/packages/staging
devpi login root --password "@verys@f3pa@ssw0rd"
devpi user -c packages email=adt-infra@google.com password=packages
devpi index -c packages/stable bases=root/pypi volatile=False
devpi index -c packages/staging bases=packages/stable volatile=True

devpi remove -y $1

# And register it with git.
dir2pi $HERE/repo
symlinks -cr $HERE
find $HERE/repo -exec git add {} \;
find $HERE/server -exec git add {} \;


