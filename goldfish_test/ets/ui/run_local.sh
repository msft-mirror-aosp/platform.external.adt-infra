#!/bin/bash
# Runs the full Android Device Hub UI ETS sequence (@goldfish_test//ets/ui:ui)
# locally on gLinux or macOS (boots an emulator, runs DeviceHubUiTest, and tests snapshot).
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
    echo "Unsupported OS for run_local.sh: $(uname -s). On Windows, use run_local.bat." >&2
    exit 1
    ;;
esac

cd "${REPO_ROOT}"
exec "${BAZEL}" test \
  "${BUILD_CONFIG}" \
  "${TEST_STRATEGY}" \
  --nocache_test_results \
  --config=sponge \
  @goldfish_test//ets/ui:ui \
  "$@"
