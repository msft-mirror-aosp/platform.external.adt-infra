import pytest
from typing import Any

CRASH_RETRIES = "CRASH_RETRIES"
CRASH_RETRY_DELAY = "CRASH_RETRY_DELAY"
CRASH_CUMULATIVE_TIMING = "CRASH_CUMULATIVE_TIMING"


class UnknownDefaultError(Exception):
    pass


class _Defaults:
    _DEFAULT_CONFIG = {
        CRASH_RETRIES: 0,  # No retries..
        CRASH_RETRY_DELAY: 0,
        CRASH_CUMULATIVE_TIMING: False,
    }

    def __init__(self) -> None:
        object.__setattr__(self, "_opts", self._DEFAULT_CONFIG.copy())

    def __getattr__(self, name: str) -> Any:
        if name in self._opts:
            return self._opts[name]
        raise UnknownDefaultError(f"{name} is not a valid default option!")

    def __setattr__(self, name: str, value: Any) -> None:
        raise ValueError(
            "Defaults cannot be overwritten manually! Please use `configure()`"
        )

    def add(self, name: str, value: Any) -> None:
        if name in self._opts:
            raise ValueError(f"{name} is already an existing default!")
        self._opts[name] = value

    def load_ini(self, config: pytest.Config) -> None:
        """
        Pytest has separate methods for loading command line args and ini options. All ini
        values are stored as strings so must be converted to the proper type.
        """
        self._opts[CRASH_RETRIES] = int(config.getini(CRASH_RETRIES.lower()))
        self._opts[CRASH_RETRY_DELAY] = float(config.getini(CRASH_RETRY_DELAY.lower()))
        self._opts[CRASH_CUMULATIVE_TIMING] = config.getini(
            CRASH_CUMULATIVE_TIMING.lower()
        )

    def configure(self, config: pytest.Config) -> None:
        if config.getini("crash_retries"):
            self.load_ini(config)
        for key in self._opts:
            if (val := config.getoption(key.lower())) is not None:
                self._opts[key] = val


Defaults = _Defaults()
