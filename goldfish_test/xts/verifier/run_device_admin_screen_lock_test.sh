#!/bin/bash
set -e

# Run automated Screen Lock Test
python3 $(dirname "$0")/pass_device_admin_screen_lock_test.py
