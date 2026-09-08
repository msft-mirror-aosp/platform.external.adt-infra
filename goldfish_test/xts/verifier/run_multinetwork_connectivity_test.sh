#!/usr/bin/env bash
# Run Multinetwork Connectivity Test.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source sourceme.rc if it exists to set CTS_APK_PATH and base CTS_OUTPUT_DIR
if [ -f "$SCRIPT_DIR/sourceme.rc" ]; then
    source "$SCRIPT_DIR/sourceme.rc"
fi
export CTS_OUTPUT_DIR="${CTS_OUTPUT_DIR:-/tmp}/multinetwork_connectivity_test"

echo "----------------------------------------------"
echo "Running: pass_multinetwork_connectivity_test.py"
echo "----------------------------------------------"

if python3 "$SCRIPT_DIR/pass_multinetwork_connectivity_test.py"; then
    echo ">>> PASSED: pass_multinetwork_connectivity_test.py"
    exit 0
else
    echo ">>> FAILED: pass_multinetwork_connectivity_test.py"
    exit 1
fi
