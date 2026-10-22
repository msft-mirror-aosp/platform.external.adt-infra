#!/bin/bash
# Runs the named snapshot ETS sequence (@goldfish_test//ets/snapshot:named_snapshot) locally on
# gLinux or macOS: builds the emulator from this checkout, cold boots it, runs NamedSnapshotTest,
# shuts it down through gRPC, relaunches it with "-snapshot ets_named" (the snapshot the test
# created over gRPC) and runs NamedSnapshotTest again with snapshot_phase=load_1.
#
# Pass --disabled to run @goldfish_test//ets/snapshot:named_snapshot_disabled instead (one cold
# boot with -no-snapshot). Other arguments are passed to bazel test. As a Bazel test, the run,
# its logs and the Tradefed results are reported to Sponge (--config=sponge); on Windows use
# run_local.bat, which reports the same way through ets/ui/report_to_sponge.bat.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"

TARGET="@goldfish_test//ets/snapshot:named_snapshot"
ARGS=()
for arg in "$@"; do
  case "$arg" in
    --disabled) TARGET="@goldfish_test//ets/snapshot:named_snapshot_disabled" ;;
    *) ARGS+=("$arg") ;;
  esac
done

case "$(uname -s)" in
  Linux*)
    BAZEL="${REPO_ROOT}/prebuilts/bazel/linux-x86_64/bazel"
    BUILD_CONFIG="--config=remote"
    ;;
  Darwin*)
    BAZEL="${REPO_ROOT}/prebuilts/bazel/darwin-x86_64/bazel"
    BUILD_CONFIG="--config=rcache"
    ;;
  *)
    echo "Unsupported OS for run_local.sh: $(uname -s). Use run_local.bat on Windows." >&2
    exit 1
    ;;
esac

cd "${REPO_ROOT}"
exec "${BAZEL}" test \
  "${BUILD_CONFIG}" \
  --strategy=TestRunner=local \
  --nocache_test_results \
  --config=sponge \
  "${TARGET}" \
  "${ARGS[@]+"${ARGS[@]}"}"
