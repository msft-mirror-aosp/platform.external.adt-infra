#!/bin/bash
# This script should allow you to run the CTS tests from a local linux box.
# In order to run this test you will have to have:
#
# - A working emulator build
# - A proper cts plan, you can use the default one this branch if you wish
# - A directory containing a cts distribution available at:
#   https://source.android.com/compatibility/cts/downloads.html
# - Have ANDROID_SDK_ROOT properly set
#
# You can edit config/local_cfg.csv to indicate which images you would like to
# run the cts against. Note that the images will be picked up from the default
# ANDROID_SDK_ROOT path.
#
#
# By default it will create a virtual python environment and install the latest
# psutils, and requests after which it will invoke the tests
#
# One way of using this script is to add it to your crontab. For example:
# 19 14   * * *   jansene export DISPLAY=:0; \
#  export ANDROID_SDK_ROOT=$HOME/Android/Sdk; \
#  $HOME/src/droid/emu-master-dev02/external/adt-infra/emu_test/run_local.sh \
#  --local-build --get-cts  >> /tmp/errlog.txt 2>&1
#
# To make sure the run will terminate (the tests sometimes get stuck) it is wise
# to add an entry to kill the process
# 08 02 * * * jansene pkill run_local
dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
option_virtualenv=yes
option_download_cts=yes
option_emu_exec=$(realpath ${dir}/../../qemu/objs/emulator)
option_emu_test=boot,cts
option_python=python
option_cts_dir=~/android-cts
option_cts_out=~/Downloads/cts/result
option_cts_plan=${dir}/test_cts/tests
option_cts_url=https://dl.google.com/dl/android/cts/android-cts-7.0_r7-linux_x86-x86.zip
option_result_dest=${dir}
red=`tput setaf 1`
green=`tput setaf 2`
reset=`tput sgr0`

# Parse out the options
for opt; do
  optarg=`expr "x$opt" : 'x[^=]*=\(.*\)'`
  case $opt in
    -h|--help|-\?) option_help=yes;;
    --no-virt) option_virtualenv=no;;
    --exec*) option_emu_exec=${optarg/#\~/$HOME} ;;
    --tests*) option_emu_test=${optarg};;
    --cts-dir*) option_cts_dir=${optarg/#\~/$HOME} ;;
    --cts-plan*) option_cts_plan=${optarg/#\~/$HOME} ;;
    --get-cts*) option_download_cts=yes;;
    --cts-url*) option_download_cts=yes; option_cts_url=${optarg} ;;
    --cts-out*) option_download_cts=yes; option_cts_out=${optarg/#\~/$HOME} ;;
    --local-build*) option_local_build=yes;;
    *)
    echo "unknown option '$opt', use --help"
    exit 1
    ;;
  esac
done

if [ "$option_help" = "yes" ] ; then
    echo "Usage: run_local.sh [options]"
    echo
    echo "Options: [defaults in brackets after descriptions]"
    echo ""
    echo "Standard options:"
    echo "  --help                      Print this message"
    echo "  --no-virt                   Do not use a python virtual_env [$option_virtualenv]"
    echo "  --exec=...                  Use the following emulator executable [$option_emu_exec]"
    echo "  --tests=...                 List of test types to run [$option_emu_test]"
    echo "  --local-build               Build the emulator in this tree and use it for the CTS test"
    echo "  --cts-dir=...               Directory containing the cts tests [$option_cts_dir]"
    echo "  --cts-plan=...              Directory containing the CTS.xml plan [$option_cts_plan]"
    echo "  --get-cts                   Download cts if not found locally"
    echo "  --get-cts-url=...           Download url with cts test, implies --get-cts [$option_cts_url]"
    echo "  --get-cts-out=...           Directory to copy cts results to, implies --get-cts [$option_cts_out]"
    echo
    echo "Make sure you have the following images available: "
    tail -n +3 config/local_cfg.csv  | awk -F "," '{ print $1 }'
    echo
    exit 1
fi

if [ -z ${ANDROID_SDK_ROOT} ]; then
  echo >&2 "You need to set ANDROID_SDK_ROOT!"
  exit 1
fi

# Setup paths, so the tests can access mksdcard, adb and can compile things
# through gradle.
export PATH=$PATH:$ANDROID_SDK_ROOT/tools:$ANDROID_SDK_ROOT/platform-tools
export ANDROID_HOME=$ANDROID_SDK_ROOT

# Download cts if needed.
if [ "$option_download_cts" = "yes" ]; then
  echo "${green}Getting the cts tests${reset}"
  ctszip=$(mktemp /tmp/cts-bundle-XXXXXXXX.zip)
  ctsdir=$(mktemp -d /tmp/cts-dir-XXXXXXXXXXXXXXX)

  # Make sure we clean up the mess on exit.
  trap "{ rm -f $ctszip; cp $ctsdir/results/*zip $option_cts_out; rm -rf $ctsdir; }" EXIT
  curl $option_cts_url -o $ctszip

  unzip $ctszip -d "${ctsdir}"
  rm -f $ctszip
  option_cts_dir=$ctsdir/android-cts
fi

if [ "$option_local_build" = "yes" ] ; then
    echo "${green}Building the emulator${reset}"
    ${dir}/../../qemu/android/rebuild.sh || (echo "${red}Failed to build emulator!"; exit 1)
    option_emu_exec=$(realpath ${dir}/../../qemu/objs/emulator)
    echo "${green}Using emulator ${option_emu_exec}${reset}"
fi

if [ ! -f ${option_emu_exec} ]; then
  echo >&2 "The emulator executable [$option_emu_exec] is not on the path"
  exit 1
fi


# Make sure the tools directory of the android_sdk_root is on the path so we can
# call mksdcard and aapt from within the python scripts.
AAPT=$(find $ANDROID_SDK_ROOT -name 'aapt' -executable | tail -n 1)
AAPT_DIR=$(dirname $AAPT)
PATH=${ANDROID_SDK_ROOT}/tools:${ANDROID_SDK_ROOT}/platform-tools:$AAPT_DIR:$PATH

# Setup the virtual python env.
if [ "$option_virtualenv" = "yes" ]; then
  if [ ! -f "venv" ]; then virtualenv ${dir}/venv; fi
  . ${dir}/venv/bin/activate
  option_python=${dir}/venv/bin/python
  pip install psutil requests
fi

# loop and run all the tests
for test in $(echo $option_emu_test| sed "s/,/ /g")
do
    echo "${green}Running the ${test} tests${reset}"
    tests="test_${test}.*"
    $option_python $dir/dotest.py -c $dir/config/local_cfg.csv -n 'localhost' -p $tests -exec $option_emu_exec --cts-dir ${option_cts_dir} --cts-plan ${option_cts_plan}
done
