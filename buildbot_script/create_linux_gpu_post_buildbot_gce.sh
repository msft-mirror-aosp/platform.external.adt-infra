# Script used to create new instances of Emulator/System Image go/ab Linux Buildbots.
# Script will create a machine named 'adt-emu-gpu-buildbot-X', where X is the first
# argument to the script and perform a basic setup.
#
# IMAGE VERSION HISTORY
# adt-emu-gpu-buildbot-1      Base Image to run emulator and system image tests

if [ $# -ne 1 ]
then echo "You must supply a positive integer to append to the adt-emu-gpu-buildbot- prefix.  Integer must not currently be in use"
fi

if [ $1 -lt 1 ]
then echo "You must supply a positive integer"
fi

export IMAGE_NAME=adt-emu-gpu-buildbot-1
export TEMP_INSTANCE=adt-emu-gpu-buildbot-$1
export PROJECT=android-studio-build
export FULL_PROJECT=android-studio-build
export ZONE=us-east1-b
export MACHINE_TYPE=n1-highmem-16
export ACCELERATOR_COUNT=1
export ACCELERATOR_TYPE=nvidia-tesla-p100
export API_SCOPES="https://www.googleapis.com/auth/logging.admin","https://www.googleapis.com/auth/monitoring","https://www.googleapis.com/auth/pubsub","https://www.googleapis.com/auth/devstorage.read_write","https://www.googleapis.com/auth/userinfo.email","https://www.googleapis.com/auth/gerritcodereview"
gcloud compute instances create $TEMP_INSTANCE --project $FULL_PROJECT --zone $ZONE --machine-type $MACHINE_TYPE --accelerator type=$ACCELERATOR_TYPE,count=$ACCELERATOR_COUNT --network default --scopes $API_SCOPES --image $IMAGE_NAME --boot-disk-size "1500GB" --boot-disk-type "pd-standard" --maintenance-policy TERMINATE --boot-disk-device-name "$TEMP_INSTANCE"

echo "Login into $TEMP_INSTANCE and run start_bb.sh from home directory as user android-build"
