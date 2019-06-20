# Script used to create new instances of Emulator/System image go/ab Windows Buildbots.
# Script will create a machine named 'adt-emu-gpu-win-X', where X is the first
# argument to the script.
# IMAGE VERSION HISTORY
# adt-emu-gpu-win-1        Base image
# adt-emu-gpu-win-1-test   Image to be used for test machines
#                             (does not start buildbot)
# adt-emu-gpu-win-1-prod   Image to be used for buildbots
#                             (starts buildbot on startup)

if [ $# -ne 2 ]
then
    echo "You must supply a positive integer to append to the adt-emu-gpu-win- prefix.  Integer must not currently be in use"
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

export IMAGE_NAME=adt-emu-gpu-win-1-$IMAGE_TYPE
export TEMP_INSTANCE=adt-emu-gpu-win-$1
export PROJECT=android-studio-build
export FULL_PROJECT=android-studio-build
export ZONE=us-east1-b
export MACHINE_TYPE=n1-highmem-16
export ACCELERATOR_COUNT=1
export ACCELERATOR_TYPE=nvidia-tesla-p100-vws
export API_SCOPES="https://www.googleapis.com/auth/logging.admin","https://www.googleapis.com/auth/monitoring","https://www.googleapis.com/auth/pubsub","https://www.googleapis.com/auth/devstorage.read_write","https://www.googleapis.com/auth/userinfo.email","https://www.googleapis.com/auth/gerritcodereview"
gcloud compute instances create $TEMP_INSTANCE --project $FULL_PROJECT --zone $ZONE --machine-type $MACHINE_TYPE --accelerator type=$ACCELERATOR_TYPE,count=$ACCELERATOR_COUNT --network default --scopes $API_SCOPES --image $IMAGE_NAME --boot-disk-size "1500GB" --boot-disk-type "pd-standard" --maintenance-policy TERMINATE --boot-disk-device-name "$TEMP_INSTANCE"
