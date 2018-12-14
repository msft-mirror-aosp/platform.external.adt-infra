# Script used to create new instances of Emulator/System image go/ab Windows Buildbots.
# Script will create a machine named 'adt-emu-win-X', where X is the first
# argument to the script.
if [ $# -ne 1 ]
then echo "You must supply a positive integer to append to the adt-emu-win- prefix.  Integer must not currently be in use"
fi

if [ $1 -lt 1 ]
then echo "You must supply a positive integer"
fi

export TEMP_INSTANCE=adt-emu-win-$1
export PROJECT=android-studio-build
export FULL_PROJECT=android-studio-build
export ZONE=us-east1-b
export MACHINE_TYPE=n1-highmem-32
export API_SCOPES="https://www.googleapis.com/auth/logging.admin","https://www.googleapis.com/auth/monitoring","https://www.googleapis.com/auth/pubsub","https://www.googleapis.com/auth/devstorage.read_write","https://www.googleapis.com/auth/userinfo.email","https://www.googleapis.com/auth/gerritcodereview"
gcloud compute instances create $TEMP_INSTANCE --project $FULL_PROJECT --zone $ZONE --machine-type $MACHINE_TYPE --network default --scopes $API_SCOPES --image "adt-emu-win" --boot-disk-size "1500GB" --boot-disk-type "pd-standard" --boot-disk-device-name "$TEMP_INSTANCE"
