#!/usr/bin/env bash
# Run Tile Service Request Test.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source sourceme.rc if it exists to set CTS_APK_PATH and base CTS_OUTPUT_DIR
if [ -f "$SCRIPT_DIR/sourceme.rc" ]; then
    source "$SCRIPT_DIR/sourceme.rc"
    # Override CTS_OUTPUT_DIR to subdirectory for this test
    export CTS_OUTPUT_DIR="$CTS_OUTPUT_DIR/tile_service_request_test"
fi

echo "----------------------------------------"
echo "Running: pass_tiles_tile_service_request_test.py"
echo "----------------------------------------"

if python3 "$SCRIPT_DIR/pass_tiles_tile_service_request_test.py"; then
    echo ">>> PASSED: pass_tiles_tile_service_request_test.py"
    exit 0
else
    echo ">>> FAILED: pass_tiles_tile_service_request_test.py"
    exit 1
fi
