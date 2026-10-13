#!/bin/bash
# Runs the //ets/foldable tests (FoldableDisplayTest) locally against an already-running
# foldable emulator on gLinux or macOS.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"

cd "${REPO_ROOT}"

case "$(uname -s)" in
  Linux*)
    exec "${REPO_ROOT}/prebuilts/bazel/linux-x86_64/bazel" test \
      --config=remote \
      --nocache_test_results \
      --config=sponge \
      @goldfish_test//ets/foldable:external_foldable \
      "$@"
    ;;
  Darwin*)
    exec "${REPO_ROOT}/prebuilts/bazel/darwin-x86_64/bazel" test \
      --config=remote \
      --nocache_test_results \
      --config=sponge \
      @goldfish_test//ets/foldable:external_foldable \
      "$@"
    ;;
  *)
    echo "Unsupported OS: $(uname -s)" >&2
    exit 1
    ;;
esac
