#!/bin/bash

# This is used to run system image UI tests.
# This will be invoked by system image source.
#  {src}/platform_testing/ui_test/run_ui_test.sh

SYSIMAGE_DIR=${1}
TARGET=${2}
BRANCH=${3}
SESSION_DIR=${SYSIMAGE_DIR}/gtest/${TARGET}

if [[ $BRANCH == *"pi"* ]]
then
    API=28
elif [[ $BRANCH == *"oc-mr1"* ]]
then
    API=27
    FILTER='{"ori":"oc-mr1"}'
elif [[ $BRANCH == *"oc"* ]]
then
    API=26
elif [[ $BRANCH == *"nyc-mr1"* ]]
then
    API=25
elif [[ $BRANCH == *"nyc"* ]]
then
    API=24
elif [[ $BRANCH == *"mnc"* ]]
then
    API=23
elif [[ $BRANCH == *"lmp-mr1"* ]]
then
    API=22
elif [[ $BRANCH == *"lmp"* ]]
then
    API=21
elif [[ $BRANCH == *"klp"* ]]
then
    API=19
elif [[ $BRANCH == *"jb-mr2-emu"* ]]
then
    API=18
fi

if [[ $TARGET == "atv" ]]
then
    IMAGE_TYPE=android-tv
elif [[ $TARGET == "gphone" ]]
then
    IMAGE_TYPE=google_apis_playstore
elif [[ $TARGET == "gwear" ]]
then
    IMAGE_TYPE=android-wear
fi

echo "Running test for $API on dist_dir $SYSIMAGE_DIR"

echo "Update SDK"
echo "Run ${ANDROID_HOME}/tools/bin/sdkmanager --update"
${ANDROID_HOME}/tools/bin/sdkmanager --update

echo "Copy and extract build"
echo "Run rm -rf ${ANDROID_HOME}/system-images/android-${API}/${IMAGE_TYPE}"
rm -rf ${ANDROID_HOME}/system-images/android-${API}/${IMAGE_TYPE}

echo "Run mkdir -p ${ANDROID_HOME}/system-images/android-${API}/${IMAGE_TYPE}"
mkdir -p ${ANDROID_HOME}/system-images/android-${API}/${IMAGE_TYPE}

echo "Run unzip -o ${SYSIMAGE_DIR}/sdk-repo-linux-system-images-*.zip -d ${ANDROID_HOME}/system-images/android-${API}/${IMAGE_TYPE}"
unzip -o ${SYSIMAGE_DIR}/sdk-repo-linux-system-images-*.zip -d ${ANDROID_HOME}/system-images/android-${API}/${IMAGE_TYPE}

mkdir -p ${SESSION_DIR}

echo "Run test"
echo "Run python -u ${ADT_INFRA}/emu_test/dotest.py --loglevel INFO --session_dir ${SESSION_DIR} --emulator $ANDROID_SDK_ROOT/emulator/emulator --test_dir UI_test --file_pattern 'test_ui.*' --config_file ${ADT_INFRA}/emu_test/config/ui_cfg.csv --buildername 'Ubuntu 14.04 HD 4400' --filter ${FILTER} --skip-adb-perf"
python -u ${ADT_INFRA}/emu_test/dotest.py --loglevel INFO --session_dir ${SESSION_DIR} --emulator $ANDROID_SDK_ROOT/emulator/emulator --test_dir UI_test --file_pattern 'test_ui.*' --config_file ${ADT_INFRA}/emu_test/config/ui_cfg.csv --buildername 'Ubuntu 14.04 HD 4400' --filter ${FILTER} --skip-adb-perf

result=$?

echo "Test Result = $result"

exit $result
