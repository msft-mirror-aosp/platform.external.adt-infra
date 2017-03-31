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
# psutils, after which it will invoke the tests

dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
option_virtualenv=yes
option_emu_exec=$(realpath ${dir}/../../qemu/objs/emulator)
option_emu_test=boot,cts,console
option_python=python
option_cts_dir=~/android-cts
option_cts_plan=${dir}/tests_cts/tests
red=`tput setaf 1`
green=`tput setaf 2`
reset=`tput sgr0`

for opt; do
  optarg=`expr "x$opt" : 'x[^=]*=\(.*\)'`
  case $opt in
    -h|--help|-\?) option_help=yes;;
    --no-virt) option_virtualenv=no;;
    --exec*) option_emu_exec=${optarg/#\~/$HOME} ;;
    --tests*) option_emu_test=${optarg};;
    --cts-dir*) option_cts_dir=${optarg/#\~/$HOME} ;;
    --cts-plan*) option_cts_plan=${optarg/#\~/$HOME} ;;
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
    echo "  --cts-dir=...               Directory containing the cts tests [$option_cts_dir]"
    echo "  --cts-plan=...              Directory containing the CTS.xml plan [$option_cts_plan]"
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

if [ ! -f ${option_emu_exec} ]; then
  echo >&2 "The emulator executable [$option_emu_exec] is not on the path"
  exit 1
fi

exit 1
# Make sure the tools directory of the android_sdk_root is on the path so we can
# call mksdcard from within the python scripts.
PATH=${ANDROID_SDK_ROOT}/tools:$PATH

# Setup the virtual python env.
if [ "$option_virtualenv" = "yes" ]; then
  if [ ! -f "local" ]; then virtualenv local; fi
  . local/bin/activate
  option_python=./local/bin/python
  pip install psutil
fi


# loop and run all the tests
for test in $(echo $option_emu_test| sed "s/,/ /g")
do
    echo "${green}Running the ${test} tests${reset}"
    tests="test_${test}.*"
    $option_python ./dotest.py -c config/local_cfg.csv -n 'localhost' -p $tests -exec $option_emu_exec --cts-dir ${option_cts_dir} --cts-plan ${option_cts_plan}
done
