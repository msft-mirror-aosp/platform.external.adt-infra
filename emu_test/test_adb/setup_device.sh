#!/bin/bash
# This script is used to flash a device with the system
# image provided.
#
# It takes 1 command line argument.
# BUILD_DIR => Absolute path for the directory containing adb,
#              fastboot and other image files.
#
# Owner: akagrawal@google.com

set -x
echo $@
env

BUILD_DIR=$1

function fastboot_wait_for_device() {
   echo "Waiting for device bootloader"
   local result=1
   while [[ $result -eq 1 ]]
   do
       sleep 2
       $FASTBOOT devices | grep $SERIAL
       result=$?
   done
}

function adb_wait_for_device() {
   echo "Waiting for sys.boot_completed=1"
   $ADB -s $SERIAL wait-for-device
   local result="0"
   while [[ "$result" != "1" ]]
   do
       result=$($ADB -s $SERIAL shell getprop sys.boot_completed | tr -d '\r')
       if [[ -z $result ]]
       then
           result="0"
       fi
       sleep 5
   done
}

function android_skip_setup_wizard() {
   echo "Skip setting wizard"
   $ADB -s $SERIAL root
   $ADB -s $SERIAL shell settings put global device_provisioned 1
   $ADB -s $SERIAL shell settings put secure user_setup_complete 1
   $ADB -s $SERIAL reboot
   adb_wait_for_device
}

function android_disable_sleep() {
   echo "Disable sleep"
   $ADB -s $SERIAL shell settings put global stay_on_while_plugged_in 7
}

function android_unlock_screen() {
   echo "Unlock screen"
   $ADB -s $SERIAL shell input keyevent 224
   sleep 1
   $ADB -s $SERIAL shell input keyevent 82
}

function android_connect_wifi() {
   echo "Connect wifi"
   $ADB -s $SERIAL shell cmd wifi connect-network $NETWORK wpa2 $WIFIKEY
}

if [[ ! -d $BUILD_DIR ]]
then
    echo "$BUILD_DIR does not exist!!!"
    exit 0
fi

ls -R $BUILD_DIR

BOOTLOADER=$BUILD_DIR/bootloader.img
RADIO=$BUILD_DIR/radio.img
SYS_IMG=$(ls builds | \grep zip)

ADB=$BUILD_DIR/adb
FASTBOOT=$BUILD_DIR/fastboot

# CODENAME should be one of supported devices
# e.g. crosshatch, flame etc
IFS='-'
read -ra ARR <<< "$SYS_IMG"
CODENAME=$ARR

# Lookup in adb devices for serial numbers
SERIAL=`$($ADB devices -l | grep $CODENAME | awk '/  device /{print $1}')

if [[ -z $SERIAL ]]
then
    echo "Device not found: $CODENAME"
    exit 0
fi

######################################
# setup builds
# Flash new system image to phone
$ADB -s $SERIAL reboot bootloader
fastboot_wait_for_device

$FASTBOOT -s $SERIAL flash bootloader $BOOTLOADER
$FASTBOOT -s $SERIAL reboot bootloader
fastboot_wait_for_device

$FASTBOOT -s $SERIAL flash radio $RADIO
$FASTBOOT -s $SERIAL reboot bootloader
fastboot_wait_for_device

# TODO Make sure ADB_VENDOR_KEYS is set on host
$FASTBOOT -s $SERIAL -w update $SYS_IMG
adb_wait_for_device

android_skip_setup_wizard
android_disable_sleep
android_unlock_screen
android_connect_wifi
######################################

exit 0
