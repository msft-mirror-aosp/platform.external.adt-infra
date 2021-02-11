#!/usr/bin/env python
"""
This file contains utility function to kill any running adb on windows.
"""

import re
import platform
import subprocess

if __name__ == '__main__':
    if "windows" in platform.system().lower():
        while True:
            out = subprocess.check_output(["C:\\PSTools\\tlist.exe", "/c"])
            if "adb.exe" not in out:
                break
            pid = re.findall('\d+', out.split("adb.exe")[0])[-1]
            print("Kill process " + pid)
            subprocess.check_output(["C:\\PSTools\\pskill.exe", "-t", pid])
