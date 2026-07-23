#!/usr/bin/env python3
"""
Delete a device screen-lock PIN via `adb shell locksettings`.

Usage: python3 delete_pin.py [PIN]
Defaults to PIN 1111 (matching create_pin.py's default) if not given.

Robustness:
- If no lock is currently set, succeeds idempotently (no-op).
- If a lock is set but does NOT verify against the given PIN, refuses to
  clear it (we can't confirm we're clearing the credential we think we
  are) and exits non-zero with a clear message, leaving it untouched.
- Verifies the lock is actually gone before reporting success.
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


def delete_pin(pin):
    if lock_disabled():
        print("No lock is currently set - nothing to do.")
        return

    if not verify_pin(pin):
        raise RuntimeError(
            f"Current lock credential does not match PIN {pin!r}. "
            "Refusing to clear an unverified credential."
        )

    out = adb("shell", "locksettings", "clear", "--old", pin)
    if "cleared" not in out.lower():
        raise RuntimeError(f"Unexpected output from clear: {out!r}")

    if not lock_disabled():
        raise RuntimeError("clear reported success but lock is still enabled")

    print(f"PIN {pin} deleted and verified.")


if __name__ == "__main__":
    pin = sys.argv[1] if len(sys.argv) > 1 else "1111"
    try:
        delete_pin(pin)
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        sys.exit(1)
