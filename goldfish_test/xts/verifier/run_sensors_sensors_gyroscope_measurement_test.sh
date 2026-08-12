#!/usr/bin/env bash
# Run Gyroscope Measurement Test.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source sourceme.rc if it exists to set CTS_APK_PATH and base CTS_OUTPUT_DIR
if [ -f "$SCRIPT_DIR/sourceme.rc" ]; then
    source "$SCRIPT_DIR/sourceme.rc"
    # Override CTS_OUTPUT_DIR to subdirectory for this test
    export CTS_OUTPUT_DIR="$CTS_OUTPUT_DIR/sensors_gyroscope_measurement_test"
fi

echo "----------------------------------------"
echo "Running: pass_sensors_sensors_gyroscope_measurement_test.py"
echo "----------------------------------------"

if python3 "$SCRIPT_DIR/pass_sensors_sensors_gyroscope_measurement_test.py"; then
    echo ">>> PASSED: pass_sensors_sensors_gyroscope_measurement_test.py"
    exit 0
else
    echo ">>> FAILED: pass_sensors_sensors_gyroscope_measurement_test.py"
    exit 1
fi
