# Embedded Emulator E2E

This contains a series of embedded emulator tests.

- You must have: `ANDROID_SDK_ROOT` set.
- You must use a supported Python compiler:
    - Linux
- Make sure your DISPLAY environment variable in linux is set to an active
  display if it is not the default one. This is usually not needed, but
  is of importance if you are using chrome remoting or are running a "fake"
  xserver.

You can run the tests as follows:

```sh
make check
```

The tests are run using [tox](https://tox.readthedocs.io/en/latest/) which will
isolate the tests and run them under Python 3.

The tests make use of fixturess to spawn and access an emulator that runs an avd.

## Development

If you wish to do development you can create a virtual
environment by running:

```sh
. ./configure
```

You can now run the tests by executing

```sh
pytest
```

You can run the test against a development emulator by:

```sh
pytest --emulator=$HOME/src/emu/external/qemu/objs/emulator
```

Where emulator points to your emulator of choice.

### Running against an already running emulator

Some test require access to the emulator logs, this means you must have run the emulator
such that it produces logs. You must have *at least* specified the following flags
and redirected the output. For example

```sh
./objs/emulator @R -verbose -debug-events -debug-time  | tee /tmp/emu.log
```

This will launch  the emulator and output the logs to /tmp/emu.log. Next you can run the
pytests as follows:

```sh
pytest  --debug_emulator_log=/tmp/emu.log --debug_emulator  -k 'test_mouse_perf_host_host_grpc'
```

This will run the test: `test_mouse_perf_host_host_grpc` against the emulator you started earlier.

### Filtering tests

You can use the standard pytest commands to run specific tests, and
reconfigure the runner by modifying tox.ini. For example you can use the `-k` flag to select
tests of interest:

## Making sure it will run successfully on the build bots

The build bots are using python 3.6. If you wish
to make sure the tests will succeed on the build bots you must have a python >3.6 interpreter
installed on your system. One easy way to manage multiple python versions is to make use
of [pyenv](https://github.com/pyenv/pyenv).

*Note*: If you use run the tests using *tox* you will automatically use the python3 interpreter.

## I would like to add some tests

You can add test according to the [pytest](https://docs.pytest.org/en/stable/) framework.
The test session will make an emulator object available for you. That is accessible
through the `avd` fixture. This is an [Emulator](emu/emulator.py) object,
which has some convenience methods to interact with the running emulator.

You can add your tests in a new .py file that automatically will be discovered.
See the [boottest](tests/test_boot.py) example below:

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

If you wish to use your own avd configuration you can set the `avd_config` dictionary to contain
the desired key = value pairs that should be used in the config.ini of the avd.

A single [module](https://docs.python.org/3/tutorial/modules.html) will use the same avd configuration.

**Note** The emulator will keep running for the duration of the test, so multiple emulators can (and likely)
will be running concurrently.

### Test Fixtures

Pytest encourages you to use [test fixtures](https://docs.pytest.org/en/6.2.x/fixture.html).
We have a set of test fixtures defined in [tests/conftest.py](tests/conftest.py) that can
be used to interact with the emulator. Here is a short list of fixtures:

- avd: Gives access to the emulator running the default avd.
- telnet: Gives access to the telnet console of the current emulator.
- adb: Function that invokes the adb executable with the given parameters.
- at_home: Rotate the emulator to portrait mode and move to the home screen.
- emulator_log: Access to the emulator logs.
- animation_app: Activates the animation app that displays a rotating triangle.
- emulator_controller: A grpc stub to the emulator controller.

### Test markers

Pytest allows you to define
[markers](https://docs.pytest.org/en/7.1.x/example/markers.html). This allows
you to mark a test with custom metadata which can be used to filter tests.

We have the following set of markers that can be used to annotate the various
tests.

- slow: marks tests as slow (deselect with '-m "not slow"')
- e2e: marks test as end to end (deselect with '-m "not e2e"')
- perf: marks test as a performance test (deselect with '-m "not perf"')
- linux: marks test as linux only, will only run if you are on linux.
- darwin: marks test as darwin only, will only run if you are on darwin.
- win32: marks test as windows only, will only run on a windows machine.

For example the test below will only run on linux:

```python
@pytest.mark.linux
def test_linux_only():
    assert sys.platform == 'linux'
```

### Dealing with flaky tests and timeouts

E2E tests are sometimes flaky. In order to combat the flakiness we make use of
the [pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures)
plugin. This plugin allows you to mark individual tests as flaky, and have them
automatically re-run when they fail, add the flaky mark with the maximum number
of times you'd like the test to run and re-run delay time in the marker:

```python
@pytest.mark.flaky(reruns=5, reruns_delay=2)
def test_example():
    import random
        assert random.choice([True, False])
```

For timeouts we make use of the [pytest-timeout](https://pypi.org/project/pytest-timeout/)
plugin. This plugin will time each test and terminate it when it takes too long.

```python
@pytest.mark.timeout(timeout=1, func_only=True)
def test_timeout():
    sleep(20)
```

## Known Issuess

Here's a list of known issues and workarounds. Most of these are related to Mac M1.

## Missing wheels

If you are using an architecture that is not supported you might find that
packages are missing. You have two options:

- Create the wheel and distribute it, see [instructions](local_repo/README.MD).
- Install requirements.txt manually i.e. `pip3 install -r requirements.txt`

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

```bash
curl -s "https://get.sdkman.io" | bash
sdk install java 8.332.08.1-amzn
sdk use java 8.332.08.1-amzn
```

This should set your default Java version to 8, after which you should be able to run the tests.
