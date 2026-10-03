#!/bin/bash
# Runs the Android Device Hub UI E2E test suite (@goldfish_test//ets/ui:ui) on Linux RBE.
# By default, video recording on RBE uses ffmpeg x11grab on Xvfb (which includes the window bar).
# Pass --cdp-video (or set CDP_VIDEO=1) to use CDP-piped video recording on RBE instead.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"

case "$(uname -s)" in
  Linux*)  BAZEL="${REPO_ROOT}/prebuilts/bazel/linux-x86_64/bazel" ;;
  Darwin*) BAZEL="${REPO_ROOT}/prebuilts/bazel/darwin-x86_64/bazel" ;;
  *)       echo "Unsupported host OS: $(uname -s)" >&2; exit 1 ;;
esac

EXTRA_ARGS=()
for arg in "$@"; do
  if [[ "${arg}" == "--cdp-video" ]]; then
    EXTRA_ARGS+=("--test_arg=--tradefed_args=--include-filter,DeviceHubUiTest,--include-filter,SnapshotUiTest,--module-arg,DeviceHubUiTest:set-option:cdp_video:true,--module-arg,SnapshotUiTest:set-option:cdp_video:true")
  else
    EXTRA_ARGS+=("${arg}")
  fi
done
if [[ "${CDP_VIDEO:-0}" == "1" || "${CDP_VIDEO:-false}" == "true" ]]; then
  EXTRA_ARGS+=("--test_arg=--tradefed_args=--include-filter,DeviceHubUiTest,--include-filter,SnapshotUiTest,--module-arg,DeviceHubUiTest:set-option:cdp_video:true,--module-arg,SnapshotUiTest:set-option:cdp_video:true")
fi

cd "${REPO_ROOT}"
exec "${BAZEL}" test \
  --config=remote \
  --sandbox_debug \
  --nocache_test_results \
  --config=ants \
  --config=sponge \
  @goldfish_test//ets/ui:ui \
  "${EXTRA_ARGS[@]}"
