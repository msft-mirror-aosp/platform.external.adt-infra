#!/usr/bin/env bash
# Run Chooser Result: Copy.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source sourceme.rc if it exists to set CTS_APK_PATH and base CTS_OUTPUT_DIR
if [ -f "$SCRIPT_DIR/sourceme.rc" ]; then
    source "$SCRIPT_DIR/sourceme.rc"
    # Override CTS_OUTPUT_DIR to subdirectory for this test
    export CTS_OUTPUT_DIR="$CTS_OUTPUT_DIR/sharesheet_chooser_result_copy_test"
fi

echo "----------------------------------------"
echo "Running: pass_sharesheet_sharesheet_chooser_result_copy_test.py"
echo "----------------------------------------"

if python3 "$SCRIPT_DIR/pass_sharesheet_sharesheet_chooser_result_copy_test.py"; then
    echo ">>> PASSED: pass_sharesheet_sharesheet_chooser_result_copy_test.py"
    exit 0
else
    echo ">>> FAILED: pass_sharesheet_sharesheet_chooser_result_copy_test.py"
    exit 1
fi
