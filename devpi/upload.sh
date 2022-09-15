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
echo "Make sure you are uploading a wheel (.whl)"
file=$1
if [ -f ${file} ] && [ ! "${file: -4}" == ".whl" ]; then
    echo "${file} should be a wheel (.whl)"
    exit 1
fi

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
devpi login root --password "@verys@f3pa@ssw0rd"
devpi use http://localhost:3141/packages/staging

if [ -f ${file} ]; then
    # Upload stuff
    twine upload -r devpi-staging --config-file  $HERE/cfg/pypirc $file
    wheel=$(basename $file)
    find $HERE/server -name $wheel -exec cp {} $HERE/repo/$WHEEL \; -exec rm {} \; -exec ln -sf $HERE/repo/$wheel {} \;
    find $HERE -name $wheel -exec git add {} \;
else
    # Download stuff
    pip download $file --index-url http://localhost:3141/packages/staging -d /tmp

    # Move it around to the right places
    FIND=$file\*
    echo "Finding $FIND"
    for wheel in $(find $HERE/server -name "$FIND"); do
        dest=$HERE/repo/$(basename $wheel)
        cp $wheel $dest
        rm $wheel
        ln -sf $dest $wheels
    done
fi

# And register it with git.
dir2pi $HERE/repo
symlinks -cr $HERE
find $HERE/repo -exec git add {} \;
find $HERE/server -exec git add {} \;


