#!/bin/bash
# Runs the embedded foldable display E2E test suite (@goldfish_test//ets/foldable:foldable) on Linux RBE.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"

case "$(uname -s)" in
  Linux*)  BAZEL="${REPO_ROOT}/prebuilts/bazel/linux-x86_64/bazel" ;;
  Darwin*) BAZEL="${REPO_ROOT}/prebuilts/bazel/darwin-x86_64/bazel" ;;
  *)       echo "Unsupported host OS: $(uname -s)" >&2; exit 1 ;;
esac

cd "${REPO_ROOT}"
exec "${BAZEL}" test \
  --config=remote \
  --sandbox_debug \
  --nocache_test_results \
  --config=ants \
  --config=sponge \
  @goldfish_test//ets/foldable:foldable \
  "$@"
