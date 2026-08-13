#!/usr/bin/env bash
# Run Biometric Tests

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source sourceme.rc if it exists to set CTS_APK_PATH and base CTS_OUTPUT_DIR
if [ -f "$SCRIPT_DIR/sourceme.rc" ]; then
    source "$SCRIPT_DIR/sourceme.rc"
    # Override CTS_OUTPUT_DIR to subdirectory for this test
    export CTS_OUTPUT_DIR="$CTS_OUTPUT_DIR/security_biometric_tests"
fi

echo "----------------------------------------"
echo "Running: pass_security_biometric_tests.py"
echo "----------------------------------------"

if python3 -u "$SCRIPT_DIR/pass_security_biometric_tests.py" "$@"; then
    echo ">>> PASSED: pass_security_biometric_tests.py"
    exit 0
else
    echo ">>> FAILED: pass_security_biometric_tests.py"
    exit 1
fi
