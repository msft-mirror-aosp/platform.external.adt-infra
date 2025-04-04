#!/bin/bash
# It is to be used with BYOB setup on cloud VMs.
# It will run UI and boot tests for system images.
#
# It takes 3 command line arguments.
# DIST_DIR => Absolute path for the distribution directory.
# API => API number for the system image
# ORI => branch code for the system image
#
# It will return 0 if it is able to execute tests, otherwise
# it will return 1.


set -x
echo $@
env

DIST_DIR=$1
API=$2
ORI=$3

function run_with_timeout () {
   ( $1 $2 $3 ) & pid=$!
   ( sleep $4 && kill -HUP $pid ) 2>/dev/null & watcher=$!
   if wait $pid 2>/dev/null; then
      pkill -HUP -P $watcher
      wait $watcher
   else
      echo "Test time out."
      # kill the process tree for test
      pkill -9 -g $pid
      rm -rf /buildbot/prebuilt/*
      exit 1
   fi
}

# Grab everything after git_emu-main-dev- starting with api.
TARGET="$(echo $DIST_DIR | sed "s/.*git_emu-main-dev-.*-\(api.*\)\/.*/\1/g")"
export ADT_INFRA='external/adt-infra'
export ANDROID_SDK_ROOT="$SDK_EMULATOR"
export JAVA_HOME="$PWD/prebuilts/studio/jdk/jdk17/linux/"
rm -rf "$ANDROID_SDK_ROOT/system-images"
ls /buildbot/src/googleplex-android/emu-main-dev/prebuilts
find /buildbot/src/googleplex-android/emu-main-dev -type d -maxdepth 2
ln -sf "$PWD/prebuilts/android-emulator-build/system-images/linux/system-images" "$ANDROID_SDK_ROOT"
ls $SDK_EMULATOR
# BUILD_DIR="out/prebuilt_cached/builds/$TARGET"

# if [[ ! -d $BUILD_DIR ]]
# then
#     echo "$BUILD_DIR does not exist!!!"
#     ls -R /buildbot/prebuilt
#     rm -rf /buildbot/prebuilt/*
#     exit 0
# fi

# ls -R $BUILD_DIR

# $ADT_INFRA has to be set on the build machine. It should have absolute path
# where adt-infra needs to be checked out.
## rm -rf $ADT_INFRA
## git clone https://android.googlesource.com/platform/external/adt-infra -b emu-main-dev $ADT_INFRA

# SDK=$SDK_SYS_IMAGE

# export ANDROID_HOME=$SDK
# export ANDROID_SDK_ROOT=$SDK

######################################
# setup builds
# rm -rf $ANDROID_HOME/system-images/android-$API/*

# (yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --licenses) & sleep 10 ; kill $!
# pkill yes
# $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --update

PHONE_PREFIX=google_phone

if [[ $API -ge 26 ]]
then
    PHONE_PREFIX=gphone
fi

PHONE_SUFFIX=sdk_addon
TV_SUFFIX=sdk

if [[ $API -ge 29 ]]
then
    PHONE_SUFFIX=userdebug
    TV_SUFFIX=user
fi

# Set image ABI
ABI=x86
if [[ $TARGET == *"x64"* ]]
then
    ABI=x86_64
fi

# Set image tag
TAG=google_apis
if [[ $TARGET == *"atv"* ]]
then
    TAG=android-tv
    TARGET=sdk_google_atv_x86-${TV_SUFFIX}
elif [[ $TARGET == *"playstore"* ]]
then
    TAG=google_apis_playstore
    TARGET=sdk_${PHONE_PREFIX}_x86-user
elif [[ $TARGET == *"x86_64"* ]]
then
    TAG=google_apis
    TARGET=sdk_${PHONE_PREFIX}_x86_64-${PHONE_SUFFIX}
else
    TAG=google_apis
    TARGET=sdk_${PHONE_PREFIX}_x86-${PHONE_SUFFIX}
fi

# PARENT_BUILD_ID=$(ls $BUILD_DIR | \grep -m 1 manifest | \grep -o -E '[0-9]{3,20}')
# touch $DIST_DIR/$PARENT_BUILD_ID

# BRANCH=$(echo $(\grep -m 1 default $BUILD_DIR/manifest_${PARENT_BUILD_ID}.xml) | awk -F'revision=' '{print $2}' | awk -F' ' '{print $1}' | awk -F'"' '{print $2}')
# PLATFORM=linux

# gsutil cp gs://android-build/builds/git_${BRANCH}-${PLATFORM}-${TARGET}/${PARENT_BUILD_ID}/*/sdk-repo-linux-system-images-${PARENT_BUILD_ID}.zip $BUILD_DIR/

# mkdir -p $ANDROID_HOME/system-images/android-$API/$TAG
# unzip -o $BUILD_DIR/sdk-repo-linux-system-images-${PARENT_BUILD_ID}.zip -d $ANDROID_HOME/system-images/android-$API/$TAG

# create filter for boot/ui tests
FILTER={\"tag\":\"$TAG\",\"ori\":\"$ORI\",\"abi\":\"$ABI\"}

# invoke test scripts
# Run Boot Tests
cmd="$ADT_INFRA/emu_test/utils/run_boot_test.sh"
run_with_timeout $cmd $DIST_DIR $FILTER 600

# Run UI Tests (Run UI tests for TAGs that are not google_apis. Run Android-tv
# UI tests on supported APIs of 26, 27 and 28).
if [[ $TAG = "google_apis_playstore" || ( $TAG = "android-tv" && $API -ge 26 && $API -le 28 ) ]]; then
    date
    echo "======================"
    cmd="$ADT_INFRA/emu_test/utils/run_ui_test.sh"
    run_with_timeout $cmd $DIST_DIR $FILTER 20800
    date
    echo "======================"
fi
######################################

# rm -rf /buildbot/prebuilt/*
