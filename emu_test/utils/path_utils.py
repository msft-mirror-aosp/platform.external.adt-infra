"""
This file contains functions that return commonly used path locations used throughout emulator testing.

This file requires the environment variable 'ANDROID_SDK_HOME' to be set, as most paths are relative to this path.
"""

import os


def get_adb_binary():
    """
    Using the current environemnt variable ANDROID_SDK_HOME, return the location of the adb command.
    :return: file location of ADB binary command.
    """
    adb_binary = os.path.join(os.environ['ANDROID_SDK_HOME'], 'platform-tools', 'adb')
    return adb_binary

