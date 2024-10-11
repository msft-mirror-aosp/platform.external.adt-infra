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
HERE=$(
    cd $(dirname $0)
    pwd
)

while [[ $# -gt 0 ]]; do
    key="$1"

    case $key in
    -f | --file)
        file=$2
        shift # arg
        shift # val
        ;;
    -d | --download)
        down=$2
        shift # arg
        shift # val
        ;;
    -r | --dir)
        dir=$2
        shift # arg
        shift # val
        ;;
    *)
        echo "Usage: $0 -f <file> -r <dir> -d <url>"
        echo "-f Install file"
        echo "-r Install directory"
        echo "-d Download and install package"
        exit 1
        ;;
    esac
done

if [ ! -z ${file} ]; then
    if [ -f ${file} ] && [ ! "${file: -4}" == ".whl" ]; then
        echo "${file} should be a wheel (.whl)"
        exit 1
    fi
fi

if [ ! -z ${dir} ]; then
    if [ ! -d ${dir} ]; then
        echo "${dir} should be a directory"
        exit 1
    fi
fi

if ! command -v symlinks &>/dev/null; then
    echo "Please intall https://github.com/brandt/symlinks.git (apt install symlinks)"
    exit 1
fi

if ! nc -z localhost 3141; then
    echo "It doesn't look like devpi is running, make sure to call ./launch-devpi.sh in a different shell"
    exit 1
fi

setup_twine() {
    # Setup twine and devpi.
    pip install devpi-client twine pip2pi
    devpi login root --password "@verys@f3pa@ssw0rd"
    devpi use http://localhost:3141/packages/staging
}

upload_file() {
    local path=$1
    twine upload -r devpi-staging --config-file $HERE/cfg/pypirc $path
    wheel=$(basename $path)
    find $HERE/server -name $wheel -exec cp {} $HERE/repo/$WHEEL \; -exec rm {} \; -exec ln -sf $HERE/repo/$wheel {} \;
    find $HERE -name $wheel -exec git add -f {} \;
}

download_package() {
    rm -rf /tmp/incoming
    local file=$1
    # Download stuff
    pip download $file --only-binary=:all: \
    --platform macosx_11_0_arm64 \
    --index-url http://localhost:3141/packages/staging -d /tmp/incoming
    pip download $file --only-binary=:all: \
    --platform macosx_10_15_x86_64 \
    --index-url http://localhost:3141/packages/staging -d /tmp/incoming
    pip download $file --only-binary=:all: \
    --platform win_amd64 \
    --index-url http://localhost:3141/packages/staging -d /tmp/incoming
    pip download $file --only-binary=:all: \
    --platform manylinux_2_17_x86_64 \
    --index-url http://localhost:3141/packages/staging -d /tmp/incoming

    # Move it around to the right places
    for fname in $(find /tmp/incoming -name '*whl'); do
        echo "Processing ${fname}"
        upload_file ${fname}
    done

}

# register all the packages with git
register_packages() {
    dir2pi $HERE/repo
    symlinks -cr $HERE
    find $HERE/repo -print0 | xargs -0 git add -f
    find $HERE/server -print0 | xargs -0 git add -f
}

setup_twine

if [ ! -z ${file} ]; then
    # Upload stuff
    upload_file $file
elif [ ! -z ${dir} ]; then
    for fname in $(find $dir -name '*whl'); do
        echo "Processing ${fname}"
        upload_file ${fname}
    done
elif [ ! -z ${down} ]; then
    download_package ${down}
fi

register_packages
