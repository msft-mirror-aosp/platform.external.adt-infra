#!/usr/bin/env bash
# Run Accelerometer Measurement Tests.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/sourceme.rc" ]; then
    source "$SCRIPT_DIR/sourceme.rc"
    export CTS_OUTPUT_DIR="$CTS_OUTPUT_DIR/sensors_accelerometer_measurement_tests"
fi

echo "----------------------------------------"
echo "Running: pass_sensors_accelerometer_measurement_tests.py"
echo "----------------------------------------"

if python3 "$SCRIPT_DIR/pass_sensors_accelerometer_measurement_tests.py"; then
    echo ">>> PASSED: pass_sensors_accelerometer_measurement_tests.py"
    exit 0
else
    echo ">>> FAILED: pass_sensors_accelerometer_measurement_tests.py"
    exit 1
fi
