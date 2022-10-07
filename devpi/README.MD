# Our local python repository

This contains the set of wheels that are available when running python scripts on the buildbots.

You can make new wheels available by running the upload.sh script. You must:

- Launch a devpi server:

    ./launch-devpi.sh


- Obtain the wheel. You should obtain a wheel for all supported platforms (M1/MacX86/Linux/Windows).

- Next you can check in the wheel of choice by running:

    ./upload.sh -f "path/to/a/wheel"

Make sure to commit all the changes, et voila, your wheels can be used.