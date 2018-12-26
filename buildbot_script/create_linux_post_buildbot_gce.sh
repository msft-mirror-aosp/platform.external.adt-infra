# Script used to create new instances of Emulator/System Image go/ab Linux Buildbots.
# Script will create a machine named 'adt-emu-buildbot-X', where X is the first
# argument to the script.
#
# IMAGE VERSION HISTORY
# adt-emu-buildbot      Base Image to run emulator and system image tests
# adt-emu-buildbot-1    Includes changes for MSVC
# adt-emu-buildbot-2    Includes set of permission fixes for MSVC

if [ $# -ne 1 ]
then echo "You must supply a positive integer to append to the adt-emu-buildbot- prefix.  Integer must not currently be in use"
fi

if [ $1 -lt 1 ]
then echo "You must supply a positive integer"
fi

export TEMP_INSTANCE=adt-emu-buildbot-$1
export PROJECT=android-studio-build
export FULL_PROJECT=android-studio-build
export ZONE=us-east1-b
export MACHINE_TYPE=n1-highmem-32
export API_SCOPES="https://www.googleapis.com/auth/logging.admin","https://www.googleapis.com/auth/monitoring","https://www.googleapis.com/auth/pubsub","https://www.googleapis.com/auth/devstorage.read_write","https://www.googleapis.com/auth/userinfo.email","https://www.googleapis.com/auth/gerritcodereview"
gcloud compute instances create $TEMP_INSTANCE --project $FULL_PROJECT --zone $ZONE --machine-type $MACHINE_TYPE --network default --scopes $API_SCOPES --image "adt-emu-buildbot-2" --boot-disk-size "1500GB" --boot-disk-type "pd-standard" --boot-disk-device-name "$TEMP_INSTANCE"
