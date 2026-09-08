#!/usr/bin/env bash
# Copyright 2026 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Run Bluetooth Classic Secure Client/Server Test.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/sourceme.rc" ]; then
    source "$SCRIPT_DIR/sourceme.rc"
    export CTS_OUTPUT_DIR="$CTS_OUTPUT_DIR/bluetooth_classic_secure_test"
fi

echo "----------------------------------------"
echo "Running: pass_bluetooth_classic_secure_test.py"
echo "----------------------------------------"

if python3 "$SCRIPT_DIR/pass_bluetooth_classic_secure_test.py"; then
    echo ">>> PASSED: pass_bluetooth_classic_secure_test.py"
    exit 0
else
    echo ">>> FAILED: pass_bluetooth_classic_secure_test.py"
    exit 1
fi
