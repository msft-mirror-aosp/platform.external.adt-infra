#!/usr/bin/env bash
# Run Event sanitization for idle UID test.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/sourceme.rc" ]; then
    source "$SCRIPT_DIR/sourceme.rc"
    export CTS_OUTPUT_DIR="$CTS_OUTPUT_DIR/sensors_event_sanitization_for_idle_uid_test"
fi

echo "----------------------------------------"
echo "Running: pass_sensors_event_sanitization_for_idle_uid_test.py"
echo "----------------------------------------"

if python3 "$SCRIPT_DIR/pass_sensors_event_sanitization_for_idle_uid_test.py"; then
    echo ">>> PASSED: pass_sensors_event_sanitization_for_idle_uid_test.py"
    exit 0
else
    echo ">>> FAILED: pass_sensors_event_sanitization_for_idle_uid_test.py"
    exit 1
fi
