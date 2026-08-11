#!/bin/bash
# Test wrapper for Device Admin Tapjacking Test
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "${SCRIPT_DIR}/pass_device_admin_tapjacking_test.py" "$@"
