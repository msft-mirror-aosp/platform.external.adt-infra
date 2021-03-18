# -*- coding: utf-8 -*-
"""stress test utilities."""

import sys
import subprocess
import platform

import emu_test.utils.path_utils as path_utils

def toBytes(s):
  PY3_OR_LATER = sys.version_info[0] >= 3

  if PY3_OR_LATER:
    return bytes(s, 'utf-8')
  else:
    return bytes(s)

def get_connected_devices():
    """Returns list of adb device ids that are connected."""
    adb_binary = path_utils.get_adb_binary()
    cmd = adb_binary + " devices"
    proc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    output, error = proc.communicate()
    connected = []
    # Collect connected devices.
    # Note that since Windows includes a carriage return, we
    # do it in a seperate loop.
    if platform.system() != 'Windows':
        for emulator_entry in output.split(toBytes('\n'))[1:]:
            if emulator_entry != '':
                connected.append(emulator_entry.split(toBytes('\t'))[0])
    else:
        for emulator_entry in output.split(toBytes('\r\n'))[1:]:
            if emulator_entry != '':
                connected.append(emulator_entry.split(toBytes('\t'))[0])
    return connected
