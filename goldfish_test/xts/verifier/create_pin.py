#!/usr/bin/env python3
"""
Create a device screen-lock PIN via `adb shell locksettings`.

Usage: python3 create_pin.py [PIN]
Defaults to PIN 1111 if not given.

Robustness:
- If no lock is currently set, sets the PIN directly.
- If a lock is already set to the SAME PIN, succeeds idempotently (no-op).
- If a lock is already set to a DIFFERENT, unknown credential, refuses to
  touch it (locksettings requires the old credential to change it, and we
  have no safe way to guess it) and exits non-zero with a clear message.
- Verifies the PIN was actually applied (lock enabled + credential
  verifies) before reporting success - a zero exit code from `adb shell`
  does not by itself guarantee the underlying command succeeded.
"""

import subprocess
import sys

SERIAL = None  # set to e.g. "emulator-5554" to target a specific device


def adb(*args, check=True):
    cmd = ["adb"]
    if SERIAL:
        cmd += ["-s", SERIAL]
    cmd += list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"adb {' '.join(args)} failed (rc={result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout.strip()


def lock_disabled():
    return adb("shell", "locksettings", "get-disabled") == "true"


def verify_pin(pin):
    out = adb("shell", "locksettings", "verify", "--old", pin, check=False)
    return "verified successfully" in out.lower()


def create_pin(pin):
    if not lock_disabled():
        if verify_pin(pin):
            print(f"PIN {pin} is already set - nothing to do.")
            return
        raise RuntimeError(
            "A screen lock is already set to a different, unknown "
            "credential. Refusing to overwrite it blindly - clear it "
            "manually (or via delete_pin.py with the correct PIN) first."
        )

    out = adb("shell", "locksettings", "set-pin", pin)
    if "pin set to" not in out.lower():
        raise RuntimeError(f"Unexpected output from set-pin: {out!r}")

    if lock_disabled():
        raise RuntimeError("set-pin reported success but lock is still disabled")
    if not verify_pin(pin):
        raise RuntimeError("set-pin reported success but verification failed")

    print(f"PIN {pin} created and verified.")


if __name__ == "__main__":
    pin = sys.argv[1] if len(sys.argv) > 1 else "1111"
    if not pin.isdigit() or len(pin) < 4:
        print("PIN must be numeric and at least 4 digits", file=sys.stderr)
        sys.exit(1)
    try:
        create_pin(pin)
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        sys.exit(1)
