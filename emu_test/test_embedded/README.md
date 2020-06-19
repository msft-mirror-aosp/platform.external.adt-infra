# Embedded Emulator E2E

This contains a series of embedded emulator tests.

You must have: `ANDROID_SDK_ROOT` set, and at least an AVD with `N` or later.

You can run the tests as follows:

    $ make check

## Development

If you wish to do development you can create a virtual
environment by running:

    $ . ./configure

You can now run the tests by executing

    $ pytest

You can run the test against a development emulator by:

    $ pytest --emulator=$HOME/src/emu/external/qemu/objs/emulator --avd=N

Where emulator points to your emulator of choice, and avd can be used to
select the avd.

You can use the standard pytest commands to run specific tests, and
reconfigure the runner by modifying tox.ini

## I would like to add some tests

You can add test according to the [pytest](https://docs.pytest.org/en/stable/) framework.
The test session will make an emulator object available for you. That is accessible
as `pytest.emulator` the is an [Emulator](emu/emulator.py) object.


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