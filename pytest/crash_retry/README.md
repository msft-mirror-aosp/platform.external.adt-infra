This is a modified version of pytest_retry that only attempts retries if the
test failed and there are emulator crashes present.

It is based on https://pypi.org/project/pytest-retry/

You can add the following markers:

```py
@pytest.mark.crash_flake(retries=3, delay=1)
def test_sometimes_crashes_the_emulator():
    # This test will be retried up to 3 times (4 attempts total)
    # if the test fails and an emulator crash occurs. There will be a
    # one second delay between each attempt.

```

Or you can have the following definitions in pytest.ini:

```ini
[pytest]
crash_retries = 2
crash_retry_delay = 0.5
crash_cumulative_timing = false
```

With cumulative timing, the duration of each test attempt is summed for the reported overall test duration. The default behavior simply reports the timing of the final attempt.