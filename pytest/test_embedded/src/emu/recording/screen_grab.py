# Copyright 2024 - The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
from abc import ABC, abstractmethod
from typing import Optional

import cv2
import numpy as np


class ScreenGrabStrategyError(Exception):
    """Exception raised when a screen grab strategy fails to initialize."""

    pass


class ScreenGrabStrategy(ABC):
    """Abstract base class for screen grabbing strategies."""

    @abstractmethod
    def get_screen_size(self, monitor: int = 0) -> tuple[int, int]:
        """Get screen dimensions for the specified monitor.

        Note: Some strategies only support monitor 0
        """
        pass

    @abstractmethod
    def grab_screen(self, monitor: int = 0) -> np.ndarray:
        """Capture screen content and return as BGR numpy array.

        Note: Some strategies only support monitor 0
        """
        pass

    @classmethod
    @abstractmethod
    def create(cls) -> Optional["ScreenGrabStrategy"]:
        """Factory method to create a strategy instance.

        A strategy is valid if the following conditions are met:

        - The packages needed for the strategy are available
        - The strategy is able to get the screen dimensions of display 0
        - The strategy is able to capture a single frame on display 0
        """
        pass


class MSSStrategy(ScreenGrabStrategy):
    """Screen grabbing strategy using MSS library."""

    def __init__(self, sct):
        self.sct = sct

    def get_screen_size(self, monitor: int = 0) -> tuple[int, int]:
        screen = self.sct.monitors[monitor]
        img = self.sct.grab(screen)
        return img.size.width, img.size.height

    def grab_screen(self, monitor: int = 0) -> np.ndarray:
        img = np.array(self.sct.grab(self.sct.monitors[monitor]))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sct.close()

    @classmethod
    def create(cls) -> Optional["MSSStrategy"]:
        """Attempts to create an MSS strategy."""
        try:
            from mss import mss

            me = cls(mss())
            screen_size = me.get_screen_size()
            frame = me.grab_screen()
            return me
        except Exception as e:
            logging.warning("Failed to initialize mss strategy: %s", e, exc_info=e)
        return None


class PILStrategy(ScreenGrabStrategy):
    """Screen grabbing strategy using PIL's ImageGrab."""

    def __init__(self):
        from PIL import ImageGrab

        self.ImageGrab = ImageGrab
        # Get initial screenshot to determine screen size
        self._initialize_screen_size()

    def _initialize_screen_size(self):
        """Initialize screen size by taking a screenshot."""
        screen = self.ImageGrab.grab()
        self.width, self.height = screen.size

    def get_screen_size(self, monitor: int = 0) -> tuple[int, int]:
        # PIL ImageGrab doesn't support multiple monitors directly
        # Returns the size of the primary screen
        return self.width, self.height

    def grab_screen(self, monitor: int = 0) -> np.ndarray:
        # PIL returns RGB format
        screenshot = self.ImageGrab.grab()
        # Convert PIL image to numpy array and convert RGB to BGR
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @classmethod
    def create(cls) -> Optional["PILStrategy"]:
        """Attempts to create a PIL strategy."""
        try:
            from PIL import ImageGrab

            me = cls()
            screen_size = me.get_screen_size()
            frame = me.grab_screen()
            return me
        except Exception as e:
            logging.warning("Failed to initialize PIL strategy: %s", e, exc_info=e)
            return None


class PyScreezeStrategy(ScreenGrabStrategy):
    """Screen grabbing strategy using PyScreeze library (used by pyautogui)."""

    def __init__(self):
        import pyscreeze

        self.pyscreeze = pyscreeze
        # Optionally configure pyscreeze to use a specific backend
        # self.pyscreeze.USE_IMAGE_NOT_FOUND_EXCEPTION = False

    def get_screen_size(self, monitor: int = 0) -> tuple[int, int]:
        # Take a screenshot to get the size
        # PyScreeze doesn't have a direct method to get screen size
        screenshot = self.pyscreeze.screenshot()
        return screenshot.size

    def grab_screen(self, monitor: int = 0) -> np.ndarray:
        # PyScreeze returns PIL Image
        screenshot = self.pyscreeze.screenshot()
        # Convert PIL image to numpy array and convert RGB to BGR
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @classmethod
    def create(cls) -> Optional["PyScreezeStrategy"]:
        """Attempts to create a PyScreeze strategy."""
        try:
            import pyscreeze

            me = cls()
            screen_size = me.get_screen_size()
            frame = me.grab_screen()
            return me
        except Exception as e:
            logging.warning(
                "Failed to initialize PyScreeze strategy: %s", e, exc_info=e
            )
            return None


class ScreenGrabStrategyFactory:
    """Factory for creating screen grab strategies with fallback support."""

    # Map of strategy names to their classes
    STRATEGIES = {
        "mss": (MSSStrategy, "MSS"),
        "pil": (PILStrategy, "PIL ImageGrab"),
        "pyscreeze": (PyScreezeStrategy, "PyScreeze"),
    }

    # Preferred order for automatic strategy selection
    PREFERRED_ORDER = ["mss", "pil", "pyscreeze"]

    @classmethod
    def create_strategy(cls, strategy_name: Optional[str] = None) -> ScreenGrabStrategy:
        """
                    Creates a screen grab strategy. If strategy_name is provided, attempts to create
                    that specific strategy. Otherwise, tries different methods in order of preference.

                    Note: You really, really want to use mss, as it is the fastest.

                    See these metrics on an Apple M1 Pro:

        --------------------------------------------------------------------------------------- benchmark 'screen_capture': 3 tests ----------------------------------------------------------------------------------------
        Name (time in ms)                                   Min                 Max                Mean             StdDev              Median                IQR            Outliers      OPS            Rounds  Iterations
        --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        test_screen_capture_performance[mss]            17.8082 (1.0)       26.4767 (1.0)       19.7869 (1.0)       1.1751 (1.0)       19.6199 (1.0)       1.6891 (1.0)         261;9  50.5385 (1.0)         820           1
        test_screen_capture_performance[pyscreeze]     431.6747 (24.24)    521.3865 (19.69)    451.7267 (22.83)    14.2485 (12.13)    450.3410 (22.95)    10.5172 (6.23)         11;4   2.2137 (0.04)         70           1
        test_screen_capture_performance[pil]           433.5235 (24.34)    464.6059 (17.55)    447.8141 (22.63)     6.0573 (5.15)     448.4781 (22.86)     8.3891 (4.97)         19;0   2.2331 (0.04)         71           1
        --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

                        Args:
                            strategy_name (Optional[str]): Name of the strategy to use.
                                                         Valid values: 'mss', 'pil', 'pyscreeze'
                                                         If None, tries all strategies in preferred order.

                        Returns:
                            ScreenGrabStrategy: The successfully created strategy.

                        Raises:
                            ScreenGrabStrategyError: If the requested strategy fails to initialize,
                                                    or if no strategy could be initialized when using
                                                    automatic selection.
                            ValueError: If an invalid strategy name is provided.
        """
        if strategy_name is not None:
            strategy_name = strategy_name.lower()
            if strategy_name not in cls.STRATEGIES:
                valid_strategies = ", ".join(f"'{s}'" for s in cls.STRATEGIES.keys())
                raise ValueError(
                    f"Invalid strategy name: '{strategy_name}'. "
                    f"Valid strategies are: {valid_strategies}"
                )

            # Try to create the specified strategy
            strategy_class, name = cls.STRATEGIES[strategy_name]
            strategy = strategy_class.create()
            if strategy:
                logging.info(f"Using {name} strategy for screen capture")
                return strategy
            else:
                raise ScreenGrabStrategyError(
                    f"Failed to initialize {name} strategy. "
                    f"Please ensure {name} is properly installed."
                )

        # If no strategy specified or if specified strategy failed,
        # try all strategies in preferred order
        for strategy_id in cls.PREFERRED_ORDER:
            strategy_class, name = cls.STRATEGIES[strategy_id]
            strategy = strategy_class.create()
            if strategy:
                logging.info("Using %s strategy for screen capture", name)
                return strategy

        raise ScreenGrabStrategyError(
            "Failed to initialize any screen grab strategy. "
            "Please ensure at least one of the following is installed: "
            "mss, Pillow, or pyscreeze"
        )
