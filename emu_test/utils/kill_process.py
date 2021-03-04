#!/usr/bin/env python
"""
This is a utility to kill a process after a timeout based on provided regex.
"""

import re
import time
import argparse
import platform
import subprocess
import os
import sys

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Provide timeout value in seconds and a regex for process name")
    parser.add_argument("--timeout", type=int, required=True, help="timeout value in seconds")
    parser.add_argument("--process_regex", type=str, required=True, help="regex for the process to be killed")
    args = parser.parse_args()

    time.sleep(args.timeout)

    self_pid = str(os.getpid())

    running_process = subprocess.check_output(["C:\\PSTools\\tlist.exe"]).split("\r\n".encode())
    py_pids = []
    for process in running_process:
        if "python.exe" in process.decode():
            pid = re.findall('\d+', process.decode())[0]
            if pid != self_pid:
                py_pids.append(pid)

    # DO NOT ADD ANY PRINT STATEMENTS IN THE SCRIPT
    # IT SHOULD PRINT ONLY STATUS AT THE END

    status=1
    for pid in py_pids:
        pid_details = subprocess.check_output(["C:\\PSTools\\tlist.exe", pid])
        if args.process_regex in pid_details.decode():
            if "windows" in platform.system().lower():
                subprocess.check_output(["C:\\PSTools\\pskill.exe", "-t", pid])
                status=0

    print(status)
