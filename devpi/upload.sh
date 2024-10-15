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
    pip install --upgrade pip
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

download_for_os() {
    local package=$1
    local os=$2
    local dest=$3
    echo ">>> Obtaining $package for $os"
    pip download $package \
    --only-binary=:all: \
    --platform $os \
    --index-url http://localhost:3141/packages/staging \
    --abi cp310 \
    -d $dest
}

download_package() {
    # Create a temporary directory
    tmpdir=$(mktemp -d)
    local file=$1
    # You can add more platforms if needed.
    for supported in \
        macosx_10_15_x86_64 \
        macosx_11_0_arm64 \
        macosx_12_0_arm64 \
        macosx_14_0_x86_64 \
        macosx_14_0_arm64 \
        manylinux_2_17_x86_64 \
        win_amd64
    do
        download_for_os $file $supported "$tmpdir"
    done

    # Move it around to the right places
    for fname in $(find "$tmpdir" -name '*whl'); do
        echo "Processing ${fname}"
        upload_file ${fname}
    done

    # Clean up the temporary directory
    rm -rf "$tmpdir"
}

# register all the packages with git
register_packages() {
    dir2pi $HERE/repo
    symlinks -cr $HERE
    find $HERE/repo -type f -name "*.html" -print0 | while IFS= read -r -d '' file; do
        # Sort the contents of the file.
        sort "$file" > "$file.tmp"
        mv "$file.tmp" "$file"
        echo "Sorted: $file"
    done
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
