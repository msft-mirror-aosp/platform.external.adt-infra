#!/bin/bash
# Runs the full Android Device Hub UI ETS sequence (@goldfish_test//ets/ui:ui)
# locally on gLinux or macOS (boots an emulator, runs DeviceHubUiTest, and tests snapshot).
#
# On Linux the Device Hub window is shown on your desktop: the DISPLAY (and
# XAUTHORITY) of this shell are passed into the test. Pass --xvfb (or set
# XVFB=1) to run inside the hermetic Xvfb display instead, as on RBE; the
# tests also fall back to Xvfb by themselves when DISPLAY is not set.
# Other arguments are passed to bazel test.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"

USE_XVFB="${XVFB:-0}"
EXTRA_ARGS=()
for arg in "$@"; do
  case "${arg}" in
    --xvfb) USE_XVFB=1 ;;
    *) EXTRA_ARGS+=("${arg}") ;;
  esac
done

DISPLAY_ARGS=()
case "$(uname -s)" in
  Linux*)
    BAZEL="${REPO_ROOT}/prebuilts/bazel/linux-x86_64/bazel"
    BUILD_CONFIG="--config=remote"
    TEST_STRATEGY="--strategy=TestRunner=local"
    if [[ "${USE_XVFB}" == "1" || "${USE_XVFB}" == "true" ]]; then
      echo "run_local.sh: running the UI tests inside the hermetic Xvfb display (--xvfb)." >&2
    elif [[ -n "${DISPLAY:-}" ]]; then
      # Bazel does not forward the environment to tests; without this the
      # tests see no DISPLAY and start Xvfb.
      DISPLAY_ARGS+=("--test_env=DISPLAY")
      [[ -n "${XAUTHORITY:-}" ]] && DISPLAY_ARGS+=("--test_env=XAUTHORITY")
      echo "run_local.sh: showing the Device Hub on DISPLAY=${DISPLAY} (pass --xvfb to use Xvfb)." >&2
    else
      echo "run_local.sh: DISPLAY is not set; the UI tests will start the hermetic Xvfb display." >&2
    fi
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
  ${DISPLAY_ARGS[@]+"${DISPLAY_ARGS[@]}"} \
  @goldfish_test//ets/ui:ui \
  ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
