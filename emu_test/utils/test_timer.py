#!/usr/bin/env python
"""
This file contains utility function to handle any timeouts in our test suits.
"""

import re
import time
import argparse
import platform
import subprocess

def run_with_timeout(timeout):
    """
    Starts a timer for a given time and will kill process tree for any testsuite running

    timeout: Value for timeout in seconds
    """
    time.sleep(timeout)

    if "windows" in platform.system().lower():
        pid = re.findall('\d+', subprocess.check_output(["C:\\PSTools\\tlist.exe", "/c"]).split("dotest")[0])[-1]
        subprocess.check_output(["C:\\PSTools\\pskill.exe", "-t", pid])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Provide timeout value in seconds")
    parser.add_argument("--timeout", type=int, required=True, help="timeout value in seconds")
    args = parser.parse_args()
    run_with_timeout(args.timeout)
