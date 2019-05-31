# Emu-image

A tool that allows you to list, boot and create docker images from all our
publicly hosted android system-images. The test will produce csv with results.
The csv can be written to a file, or printed to std out.

## Getting Started

In order to use this you will need to:

- Have a valid acloud configuration:

  For example:

  ```
  project: "my-super-project"
  zone: "us-west1-b"
  client_id: "my-client-id"
  client_secret: "aSup3rS@f3Secret!"
  # Must have this one otherwise you will not boot.
  stable_goldfish_host_image_name: "vsoc-host-scratch-me"
  ssh_private_key_path: "/home/me/.ssh/acloud_rsa"
  ssh_public_key_path: "/home/me/.ssh/acloud_rsa.pub"
  storage_bucket_name: "my-super-project"
  # Note these two below are crucial!
  orientation: "portrait"
  resolution: "800x1280x32x213"
  extra_scopes: "https://www.googleapis.com/auth/androidbuild.internal"
  ```

**Note:** You will likely need the extra_scopes line. Acloud will not generate this by default for you. The scope enables your base image to access the internal build API.

- Have the acloud module installed. The acloud module can be found in AOSP under tools/acloud. If you are building this from the emulator repo you can just:

  ```sh
  $ push ../../../tools/acloud
  $ python setup.py install --user
  $ popd
  ```

- Install this module yourself
  ```sh
  $ python setup.py install --user
  ```

Now you can launch images by using emu-image.

**NOTE:** This tool will require access to http://go/ab. The tool will try to authenticate. If this will fail on the first time and the tool becomes interactive.
You will have to click on a redirect link and enter the generated token. _This means the first run to obtain this token cannot use concurrency!_.

```sh
$ emu-image --helpfull
```

For example, to boot all the images with api level 25 you can:

```sh
$ emu-image --boot "25" -v 0 --build_id 5134463
```

This will produce a csv that could look like this:

    Output:

    api, tag, abi, zip, url, can_boot
    25, android-tv, x86, x86-25_r13.zip, https://dl.google.com/android/repository/sys-img/android-tv/x86-25_r13.zip, True
    25, android-wear, armeabi-v7a, armeabi-v7a-25_r03.zip, https://dl.google.com/android/repository/sys-img/android-wear/armeabi-v7a-25_r03.zip, False
    25, android-wear, x86, x86-25_r03.zip, https://dl.google.com/android/repository/sys-img/android-wear/x86-25_r03.zip, True
    25, android, x86, x86-25_r01.zip, https://dl.google.com/android/repository/sys-img/android/x86-25_r01.zip, True
    25, android, x86_64, x86_64-25_r01.zip, https://dl.google.com/android/repository/sys-img/android/x86_64-25_r01.zip, True
    25, google_apis_playstore, x86, x86-25_r09.zip, https://dl.google.com/android/repository/sys-img/google_apis_playstore/x86-25_r09.zip, True

    Emulator build: 5134463

To boot a set of images of go/ab with the latest emu-master-dev emulator build:

```sh
$ emu-image --boot "5538743,5534473"
```

## Creating docker images

You can create docker images by using the --create flag. For example:

```sh
$ emu-image --create  "28, google_apis_playstore, x86_64, x86_64-Q_r04.zip"
```

Will create the following docker image:

| REPOSITORY                               | TAG    | IMAGE ID     | CREATED        | SIZE   |
| ---------------------------------------- | ------ | ------------ | -------------- | ------ |
| emulator/google_apis_playstore-28-x86_64 | latest | de8a974c8a4b | 53 seconds ago | 4.07GB |

You can launch the docker image as follows:

```sh
$ docker run -e "ADBKEY=$(cat ~/.android/adbkey)" --privileged  --publish 5556:5556/tcp --publish 5555:5555/tcp emulator/google_apis_playstore-28-x86_64
```

The command line parameters mean the following:

- `-e "ADBKEY=$(cat ~/.android/adbkey)"` Set the environment variable ADBKEY to contain the private key used by your current adb install. Usually this private
  key resides in ~/.android/adbkey
- `--privileged` The emulator needs access to kvm, hence you will need to pass the --privileged flag. Without docker will not have access to KVM and you will not be able run the emulator.
- `--publish 5556:5556/tcp` make the internal port 5556 in the docker container visible to the outside world at port 5556. This is the gRPC port, that can be used to interact with the emulator.
- `--publish 5555:5555/tcp` make the internal port 5555 in the docker container visible to the outside world at port 5555. This is the ADB port that can be used to interact with the emulator.

### Pushing docker images to internal repo

You can push the created images to an internal repo as follows:

1. First we need to make sure you have GCE configured such that we can publish
   the docker images to our GCE project.

   ```sh
   $ gcloud auth configure-docker
   ```

2. Next you can push an image to the emu-dev-cts project as follows:

   ```
   $ docker push gcr.io/emu-dev-cts/emulator/google_apis_playstore-28-x86_64:5550274
   ```

3. Now you can pull the image

### Troubleshooting

- I see access errors when creating a docker image.

  This workflow requires sudoless Docker. Add your user to the docker group to run Docker commands without 'sudo':

  ```sh
     sudo adduser $USER docker
  ```

  In order for the above to take effect, logout and log back in or use `newgrp docker` to change your primary group within a terminal.

## Some things to be aware of- It will kill your running adb server, as we need to modify the credential search path.

- Public images are signed and will not allow adb access without proper verification.
- When ADB makes a connection to a device it goes through ADBD. ADBD will negotiate credentials to the device on behalf of your ADB client.
- You can have only one instance of an ADBD running on your machine.
- During first launch the emulator will marshall the keys found in ~/.android/adbkey to the emulated device.
- We will obtain this key and place it in the credentials search path of our ADB deamon, so adb can offer the key and connect to the device.
- You can launch gpu enabled images, they might be expensive, and you must make sure you have enough GPU quota available.

- You will need to have ssh access to your GCE instances from the machine you are running this from. For example if you are using the emu-dev-cts project you will have to be within google corpnet.

- The default logging level is info, which causes some of the internal modules to log a lot of information.

- This tools does its best to terminate machines after launch completion. However interrupting or specifying the -nodelete flag can cause machines to linger

- Be careful with the concurrency flag, as you could quickly go over CPU/Address quota in gce.
