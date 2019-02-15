#!/bin/bash
# This is used to setup system image builds..
# This will be invoked by system image source.
#  {src}/platform_testing/ui_test/run_test.sh

BUILD_DIR=$1
API=$2

echo "Update SDK"
echo "Run $ANDROID_HOME/tools/bin/sdkmanager --update"
yes | $ANDROID_HOME/tools/bin/sdkmanager --licenses
$ANDROID_HOME/tools/bin/sdkmanager --update

rm -rf $ANDROID_HOME/system-images/android-$API/*

echo "Copy and extract builds"
for FILE in "$BUILD_DIR"/*
do
    FILENAME=$(basename $FILE)
    if [[ $FILENAME == *"tv"* ]]
    then
        IMAGE_TYPE=android-tv
    elif [[ $FILENAME == *"wear"* ]]
    then
        IMAGE_TYPE=android-wear
    elif [[ $FILENAME == *"user"* ]]
    then
        IMAGE_TYPE=google_apis_playstore
    else
        IMAGE_TYPE=google_apis
    fi

    echo "Run mkdir -p $ANDROID_HOME/system-images/android-$API/$IMAGE_TYPE"
    mkdir -p $ANDROID_HOME/system-images/android-$API/$IMAGE_TYPE

    echo "Run unzip -o $BUILD_DIR/$FILENAME/* -d $ANDROID_HOME/system-images/android-$API/$IMAGE_TYPE"
    unzip -o $BUILD_DIR/$FILENAME/* -d $ANDROID_HOME/system-images/android-$API/$IMAGE_TYPE
done

echo "Setup complete"
