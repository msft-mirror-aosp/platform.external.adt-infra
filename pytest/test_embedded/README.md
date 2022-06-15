# Embedded Emulator E2E

This contains a series of embedded emulator tests.

- You must have: `ANDROID_SDK_ROOT` set.
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

When you run a test the following will happen:

- A default Pixel2 avd will be created with system image
  31-x86-google_apis_playstore
- The emulator will launch the avd
- The runner will wait until the avd is boot complete
- The set of selected tests will run

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
pytest --emulator=$HOME/src/emu/external/qemu/objs/emulator --avd=N
```

Where emulator points to your emulator of choice, and avd can be used to
select the avd.

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

## Making sure it will run successfully on the build bots.

The build bots are using python 3.6. If you wish
to make sure the tests will succeed on the build bots you must have a python >3.6 interpreter
installed on your system. One easy way to manage multiple python versions is to make use
of [pyenv](https://github.com/pyenv/pyenv).

*Note*: If you use run the tests using *tox* you will automatically use the python3 interpreter.

## I would like to add some tests

You can add test according to the [pytest](https://docs.pytest.org/en/stable/) framework.
The test session will make an emulator object available for you. That is accessible
as `pytest.emulator` this is an [Emulator](emu/emulator.py) object, which has some convenience
methods to interact with the running emulator.

You can add your tests in a new .py file that automatically will be discovered.
See the [boottest](tests/test_boot.py) example below:

```python
import pytest
from google.protobuf import empty_pb2

@pytest.mark.e2e
def test_booted():
    """Make sure the emulator status is set to booted."""
    grpc = pytest.emulator.get_emulator_controller()
    response = grpc.getStatus(empty_pb2.Empty())
    assert response.booted
```

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
