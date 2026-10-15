#!/bin/bash
# Runs the embedded foldable display ETS sequence (@goldfish_test//ets/foldable:foldable)
# locally on gLinux or macOS (boots a Pixel Fold AVD with -qt-hide-window, runs
# FoldableDisplayTest, and verifies snapshot relaunch).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"

case "$(uname -s)" in
  Linux*)
    BAZEL="${REPO_ROOT}/prebuilts/bazel/linux-x86_64/bazel"
    BUILD_CONFIG="--config=remote"
    TEST_STRATEGY="--strategy=TestRunner=local"
    ;;
  Darwin*)
    BAZEL="${REPO_ROOT}/prebuilts/bazel/darwin-x86_64/bazel"
    BUILD_CONFIG="--config=rcache"
    TEST_STRATEGY="--strategy=TestRunner=local"
    ;;
  *)
    echo "Unsupported OS for run_local.sh: $(uname -s)." >&2
    exit 1
    ;;
esac

cd "${REPO_ROOT}"
exec "${BAZEL}" test \
  "${BUILD_CONFIG}" \
  "${TEST_STRATEGY}" \
  --nocache_test_results \
  --config=sponge \
  @goldfish_test//ets/foldable:foldable \
  "$@"
