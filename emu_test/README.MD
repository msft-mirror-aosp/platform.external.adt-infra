Android Emulator Integration Tests
==================================

In this directory you will find a set of integration tests that are run as part of every build.


## I'm a developer

If you are a developer you will likely want to run the tests as you go. You can do this as follows:



- First make sure you have an emulator build and have all the python requirements installed
  ```sh

  export AOSP=~/src/emu-master-dev # Point to your root..
  cd $AOSP/external/qemu && android/rebuild
  pip install -r $AOSP/external/adt-infra/emu_test/requirements.txt
  ```


- Next set your test pattern and config file. The example below assumes you are
  running the grpc test against the snapshot avd configurations.

```sh
 export TEST_PATTERN='test_grpc.*'
 export CONFIG_FILE=external/adt-infra/emu_test/config/snapshot_cfg_byob.csv
 ```

- Next you can launch the test you are interested in as follows:

```sh
  cd $AOSP; \
  rm -rf /tmp/test/; mkdir -p /tmp/test; \
  ninja -C $AOSP/external/qemu/objs &&
  python -u external/adt-infra/emu_test/dotest.py \
   --loglevel DEBUG \
   --session_dir /tmp/test \
   --emulator $AOSP/external/qemu/objs/emulator \
   --test_dir gprc_test \
   --file_pattern $TEST_PATTERN \
   --buildername Linux \
   --config_file $CONFIG_FILE \
   --skip-adb-perf  \
   --generate_xml
```