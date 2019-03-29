Emu-image
=========
A tool that allows you to list and boot all our publicly hosted images. The test will produce csv with results. The csv can be written to a file, or printed to std out.

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
   stable_goldfish_host_image_name: "vsoc-host-scratch-jansene"
   ssh_private_key_path: "/home/me/.ssh/acloud_rsa"
   ssh_public_key_path: "/home/me/.ssh/acloud_rsa.pub"
   storage_bucket_name: "my-super-project"
   # Note these two below are crucial!
   orientation: "portrait"
   resolution: "800x1280x32x213"
   ```

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


```sh
   emu-image --help
```

For example, to boot all the images with api level 25 you can:
```sh
   emu-image --boot "25" -v 0 --build_id 5134463
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


## Some things to be aware of

- It will kill your running adb server, as we need to modify the credential search path.

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
