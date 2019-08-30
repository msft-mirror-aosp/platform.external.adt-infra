#!/usr/bin/env python
"""
This file contains utility function to kill any running adb on windows.
"""

import re
import platform
import subprocess

if __name__ == '__main__':
    if "windows" in platform.system().lower():
        pid = re.findall('\d+', subprocess.check_output(["C:\\PSTools\\tlist.exe", "/c"]).split("adb")[0])[-1]
        subprocess.check_output(["C:\\PSTools\\pskill.exe", "-t", pid])
