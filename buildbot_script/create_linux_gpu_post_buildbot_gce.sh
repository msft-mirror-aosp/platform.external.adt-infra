# Script used to create new instances of Emulator/System Image go/ab Linux Buildbots.
# Script will create a machine named 'adt-emu-gpu-buildbot-X', where X is the first
# argument to the script and perform a basic setup.
#
# IMAGE VERSION HISTORY
# adt-emu-gpu-buildbot-1        Base Image to run emulator and system image tests
# adt-emu-gpu-buildbot-2        Fixes nvidia module issue after reboot
# adt-emu-gpu-buildbot-2-test   Image to be used for test machines
#                                (does not start buildbot)
# adt-emu-gpu-buildbot-2-prod   Image to be used for buildbots
#                                (starts buildbot on startup)
# adt-emu-gpu-buildbot-3-test   Updated nVidia driver 418.70
#                                (does not start buildbot)
# adt-emu-gpu-buildbot-3-prod   Updated nVidia driver to 418.70
#                                (starts buildbot on startup)

if [ $# -ne 2 ]
then
    echo "You must supply a positive integer to append to the adt-emu-buildbot- prefix.  Integer must not currently be in use"
    echo "You must supply an image type, either prod or test."
    exit -1
fi

if [ $1 -lt 1 ]
then
    echo "You must supply a positive integer"
    exit -1
fi

export IMAGE_TYPE="test"
if [ $2 == "prod" ]
then
   export IMAGE_TYPE="prod"
fi

export IMAGE_NAME=adt-emu-gpu-buildbot-3-$IMAGE_TYPE
export TEMP_INSTANCE=adt-emu-gpu-buildbot-$1
export PROJECT=android-studio-build
export FULL_PROJECT=android-studio-build
export ZONE=us-east1-b
export MACHINE_TYPE=n1-highmem-16
export ACCELERATOR_COUNT=1
export ACCELERATOR_TYPE=nvidia-tesla-p100-vws
export API_SCOPES="https://www.googleapis.com/auth/logging.admin","https://www.googleapis.com/auth/monitoring","https://www.googleapis.com/auth/pubsub","https://www.googleapis.com/auth/devstorage.read_write","https://www.googleapis.com/auth/userinfo.email","https://www.googleapis.com/auth/gerritcodereview"
gcloud compute instances create $TEMP_INSTANCE --project $FULL_PROJECT --zone $ZONE --machine-type $MACHINE_TYPE --accelerator type=$ACCELERATOR_TYPE,count=$ACCELERATOR_COUNT --network default --scopes $API_SCOPES --image $IMAGE_NAME --boot-disk-size "1500GB" --boot-disk-type "pd-standard" --maintenance-policy TERMINATE --boot-disk-device-name "$TEMP_INSTANCE"

echo "Login into $TEMP_INSTANCE and run start_bb.sh from home directory as user android-build"
