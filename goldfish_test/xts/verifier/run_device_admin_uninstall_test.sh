#!/bin/bash
# Test wrapper for Device Admin Uninstall Test
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "${SCRIPT_DIR}/pass_device_admin_uninstall_test.py" "$@"
