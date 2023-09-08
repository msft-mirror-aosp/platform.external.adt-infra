# Embedded Emulator E2E

This contains a series of integration tests that validate that the emulator works as expected under various configurations.

We write the integration tests in pytest and run them as part of the automated build process. The tests are launched using the run_tests.py script. The script roughly does the following:

* Creates a temporary directory with a virtual environment
* Installs all the dependencies
* Sets up ANDROID_SDK_ROOT to point to $AOSP_ROOT / "prebuilts"  / "android-emulator-build" / "system-images" / OS_NAME
* Loads the test definitions from [cfg/emulator_tests.json](cfg/emulator_tests.json)
* Launches pytest to run all the tests defined in the test configuration

## Test configuration file

The test configuration file is a json file that describes which set of
tests to run under a given configuration. It has the following format:

```json
  {
    "test_suite_1" : xxx,
    "test_suite_2" : xxx,
  }
```

Where xxx descibes a test as follows:

```json
 "landscape_test_suite": {
       // This contains a human readable description of what this suite should do
        "description": "Set of tests that verify that graphic related tests work well in a `landscape` emulator",
        // Set of flags to pass to the emulator when it gets launched.
        // for example "-qt-hide-window" will run as an embedded emulator
        "launch_flags": [],
        // Set of flags to pass to the pytest launcher, in this case only test
        // marked as graphics will be run
        "pytest_flags": [
            "-m graphics"
        ],
        // The avd configuration that will be used when running these tests.
        "avd_config": {
            "api": "33",
            "tag.id": "google_apis",
            "hw.initialOrientation": "landscape",
            "skin.name" : "1280x720"
        }
    },
```

You can select which suite to run by passing in the `--run_suite` flag. Every suite description matching the regex will be executed.

## Running the tests on your local machine

To run the tests on your local machine, you can run `run_tests.sh` on Posix or `run_tests.cmd` on Windows. You will need to provide the path to the emulator binary using the `-e` flag.

If you have a local build you could launch it with the symbols flag to use the symbols produced during build:

   run_tests.sh -e ~/src/emu-master-dev/external/qemu/objs/emulator --symbols ~/src/emu-master-dev/external/qemu/objs/build/symbols

Note that we are using the AOSP python interpreter, which has limitations. For example, we have no symbols and TLS.

### Running tests with your local python interpreter

You can work around this by using your own python install. For example, you could use pyenv:

* Install PyEnv (`brew install pyenv`)
* Install Python 3.10.6 (`pyenv install 3.10.6`)
* Create a new virtual environment (`python -m venv .venv`)
* Activate the virtual environment (`source .venv/bin/activate`)
* Run run_tests.sh with the `--no-aosp` flag and the path to the emulator binary

For example:

    run_tests.sh -e ~/src/emu-master-dev/external/qemu/objs/emulator --symbols ~/src/emu-master-dev/external/qemu/objs/build/symbols --no-aosp

Now you can use your own python tools to inspect issues.

## Development

To create a virtual environment, run `. ./configure.sh` This will install a virtual environment in the .venv directory and install all the dependencies required to run the tests.

You can run a subset of the tests with an already running emulator. In order
to do so you will have to launch the emulator with an avd that you will use for the tests. You can see details on this in the section below.

    pytest --debug_emulator -k "name_of_the_test"


### Running tests from a suite

If you wish to run a test from a suite you will have to pass in the right parameters. You can find the exact details in the [cfg/emulator_tests.json](cfg/emulator_tests.json) file. For example to run the landscape test suite from the command line can run:

      pytest -m graphics and not multidisplay \
           --timeout=300 \
           --emulator=~/src/emu/external/qemu/objs/emulator \
           --avd_config '{
            "api": "33",
            "tag.id": "google_apis",
            "hw.initialOrientation": "landscape",
            "skin.name": "1280x720"
          }'  \
          --emulator_launch_flags '["-no-snapshot]'

## Obtaining new packages with devpi

The virtual environment is using the python interpreter in AOSP. This interpreter does
not support TLS, and hence you will not be able to install external packages. To work
around this you can run a local devpi server using a python interpreter that does support
tls.

Devpi can be run by running a devpi server that is found here: [../../devpi/](../../devpi).

  + Change to the `../../devpi` directory.
  + Run the `./launch_devpi.sh` script.

ie:

    cd ../../devpi
    ./launch_devpi.sh

Once the devpi server is running, you can install packages from the devpi repository by running the following command:

    pip install <package_name>

For example, to install the py-spy package, you would run the following command:

  pip install py-spy

### Running against an already running emulator

Some test require access to the emulator logs, this means you must have run the emulator such that it produces logs. You must have *at least* specified the following flags and redirected the output. For example

    ./objs/emulator @R -verbose -debug-events -debug-time  | tee /tmp/emu.log

This will launch  the emulator and output the logs to /tmp/emu.log. Next you can run the pytests as follows:

    pytest  --debug_emulator_log=/tmp/emu.log --debug_emulator  -k 'test_mouse_perf_host_host_grpc'

This will run the test: `test_mouse_perf_host_host_grpc` against the emulator you started earlier.

### Filtering tests

You can use the standard pytest commands to run specific tests, and reconfigure the runner by modifying tox.ini. For example you can use the `-k` flag to select tests of interest:

## Making sure it will run successfully on the build bots

If you are adding new packages you must make them available in our on disk repository. This means you will have to install the dependencies in our local repo. See [../../devpi/README. MD](../../devpi/README. MD) for more information.

## I would like to add some tests

You can add test according to the [pytest](https://docs.pytest.org/en/stable/) framework. The test session will make an emulator object available for you. That is accessible through the `avd` fixture. This is an [Emulator](emu/emulator.py) object, which has some convenience methods to interact with the running emulator.

You can add your tests in a new .py file that automatically will be discovered. See the [boottest](tests/test_boot.py) example below:

```python
import pytest
from google.protobuf import empty_pb2

# Use a custom avd configuration, vs. the default
avd_config = {"api": "33", "tag.id": "google_apis"}

@pytest.mark.e2e
def test_booted(emulator_controller):
    """Make sure the emulator status is set to booted."""
    response = emulator_controller.getStatus(empty_pb2.Empty())
    assert response.booted
```

If you wish to use your own avd configuration you can set the `avd_config` dictionary to contain the desired key = value pairs that should be used in the config.ini of the avd.

A single [module](https://docs.python.org/3/tutorial/modules.html) will use the same avd configuration.

**Note** The emulator will keep running for the duration of the test, so multiple emulators can (and likely) will be running concurrently.

### Test Fixtures

Pytest encourages you to use [test fixtures](https://docs.pytest.org/en/6.2.x/fixture.html). We have a set of test fixtures defined in [tests/conftest.py](tests/conftest.py) that can be used to interact with the emulator. Here is a short list of fixtures:

* avd: Gives access to the emulator running the default avd.
* telnet: Gives access to the telnet console of the current emulator.
* adb: Function that invokes the adb executable with the given parameters.
* at_home: Rotate the emulator to portrait mode and move to the home screen.
* emulator_log: Access to the emulator logs.
* animation_app: Activates the animation app that displays a rotating triangle.
* emulator_controller: A grpc stub to the emulator controller.

### Test markers

Pytest allows you to define [markers](https://docs.pytest.org/en/7.1.x/example/markers.html). This allows you to mark a test with custom metadata which can be used to filter tests.

We have the following set of markers that can be used to annotate the various
tests.

  + adb: marks test as adb test.
  + boot: marks tests as boot test, these tests validate that something hold just after booting. (deselect with '-m "not boot"')
  + console: mark tests related to the emulator console
  + darwin: marks test as darwin only, will only run if you are on darwin.
  + e2e: marks test as end to end (deselect with '-m "not e2e"')
  + embedded: marks test as embedded only, will run on an embedded emulator.
  + foldable: marks test that operates on a foldable emulator
  + graphics: marks tests related to graphics operations
  + hardware: marks test as a low-level hardware test
  + linux: marks test as linux only, will only run if you are on linux.
  + perf: marks test as a performance test (deselect with '-m "not perf"')
  + resizable: marks test that should run on a resizable emulator
  + slow: marks tests as slow (deselect with '-m "not slow"')
  + snapshot: marks tests related to snapshot operations
  + multidisplay: mark tests related to multidisplay
  + win32: marks test as windows only, will only run on a windows machine.

For example the test below will only run on linux:

```python
  @pytest.mark.linux
  def test_linux_only():
      assert sys.platform == 'linux'
  ```

You can find all the markers, and the description, in the [pytest.ini](pytest.ini) file.

### Dealing with flaky tests and timeouts

E2E tests are sometimes flaky. In order to combat the flakiness we make use of the [pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures) plugin. This plugin allows you to mark individual tests as flaky, and have them automatically re-run when they fail, add the flaky mark with the maximum number of times you'd like the test to run and re-run delay time in the marker:

```python
  @pytest.mark.flaky(reruns=5, reruns_delay=2)
  def test_example():
      import random
          assert random.choice([True, False])
  ```

For timeouts we make use of the [pytest-timeout](https://pypi.org/project/pytest-timeout/) plugin. This plugin will time each test and terminate it when it takes too long.

```python
  @pytest.mark.timeout(timeout=1, func_only=True)
  def test_timeout():
      sleep(20)
  ```

## Known Issuess

Here's a list of known issues and workarounds. Most of these are related to Mac M1.

## Missing wheels

If you are using an architecture that is not supported you might find that
packages are missing. You must check in these packages in our local (on disk)
repository. See [README. MD](../../devpi/README. MD) for details on how to do this.

### Java exceptions on Pytest log

If you see exceptions like the following when running pytest:

```java
Exception in thread "main" java.lang.NoClassDefFoundError: javax/xml/bind/annotation/XmlSchema
  at com.android.repository.api.SchemaModule$SchemaModuleVersion.<init>(SchemaModule.java:156)
  at com.android.repository.api.SchemaModule.<init>(SchemaModule.java:75)
  at com.android.sdklib.repository.AndroidSdkHandler.<clinit>(AndroidSdkHandler.java:81)
  at com.android.sdklib.tool.sdkmanager.SdkManagerCli.main(SdkManagerCli.java:73)
  at com.android.sdklib.tool.sdkmanager.SdkManagerCli.main(SdkManagerCli.java:48)
Caused by: java.lang.ClassNotFoundException: javax.xml.bind.annotation.XmlSchema
  at java.base/jdk.internal.loader.BuiltinClassLoader.loadClass(BuiltinClassLoader.java:581)
  at java.base/jdk.internal.loader.ClassLoaders$AppClassLoader.loadClass(ClassLoaders.java:178)
  at java.base/java.lang.ClassLoader.loadClass(ClassLoader.java:522)
  ... 5 more
```

You are likely not using the right java version for sdkmanager. The easiest solution
is to install a java 8 runtime using [sdkman](https://sdkman.io/)

For example:

    curl -s "https://get.sdkman.io" | bash
    sdk install java 8.332.08.1-amzn
    sdk use java 8.332.08.1-amzn

This should set your default Java version to 8, after which you should be able to run the tests.
