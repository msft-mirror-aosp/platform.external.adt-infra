# Copyright 2025 - The Android Open Source Project
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

import pathlib
import platform

DIR_PREFIX = ("home = ", "base-prefix = ", "base-exec-prefix = ")
PYTHON_PREFIX = "base-executable = "

def main():
    # This is only needed for windows.
    if platform.system() != "Windows":
        return
    base_dir = pathlib.Path(__file__).resolve().parent
    python_dir = base_dir.joinpath("windows-x86")
    venv_cfg = base_dir.joinpath(".venv", "pyvenv.cfg")
    lines = venv_cfg.read_text().splitlines()
    for i, ln in enumerate(lines):
        for p in DIR_PREFIX:
            if ln.startswith(p):
                lines[i] = p + str(python_dir) + "\r\n"
                break
        if ln.startswith(PYTHON_PREFIX):
            lines[i] = PYTHON_PREFIX + str(python_dir.joinpath("python.exe")) + "\r\n"
    venv_cfg.write_text("".join(lines))


if __name__ == "__main__":
    main()
