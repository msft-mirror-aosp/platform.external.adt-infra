#!/bin/bash
# Runs DeviceHubUiTest locally against an already-running emulator on gLinux, macOS, or Windows (Git Bash/MSYS).
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
      @goldfish_test//ets/ui:external_ui \
      "$@"
    ;;
  Darwin*)
    exec "${REPO_ROOT}/prebuilts/bazel/darwin-x86_64/bazel" test \
      --config=remote \
      --nocache_test_results \
      --config=sponge \
      @goldfish_test//ets/ui:external_ui \
      "$@"
    ;;
  MINGW*|MSYS*|CYGWIN*)
    BAZEL="${REPO_ROOT}/prebuilts/bazel/windows-x86_64/bazel.exe"
    "${BAZEL}" build @goldfish_test//ets:android_ets_zip @goldfish//emulator/launcher:android-device-hub
    ETS_ZIP="$("${BAZEL}" cquery --output=files @goldfish_test//ets:android_ets_zip | tr -d '\r')"
    HUB_DIR="$("${BAZEL}" cquery --output=files @goldfish//emulator/launcher:android-device-hub | tr -d '\r')"
    WORK_DIR="$(mktemp -d)"
    trap 'rm -rf "${WORK_DIR}"' EXIT
    unzip -q "${REPO_ROOT}/${ETS_ZIP}" -d "${WORK_DIR}"
    "${WORK_DIR}/android-ets/tools/ets-tradefed.bat" run commandAndExit ets \
      --include-filter DeviceHubUiTest \
      --include-filter SnapshotUiTest \
      --module-arg "DeviceHubUiTest:set-option:device_hub_path:${REPO_ROOT}/${HUB_DIR}" \
      --module-arg "DeviceHubUiTest:set-option:display_dir:${REPO_ROOT}/tools/emulator/testlib/display" \
      --module-arg "SnapshotUiTest:set-option:device_hub_path:${REPO_ROOT}/${HUB_DIR}" \
      --module-arg "SnapshotUiTest:set-option:display_dir:${REPO_ROOT}/tools/emulator/testlib/display" \
      "$@"
    ;;
  *)
    echo "Unsupported OS: $(uname -s)" >&2
    exit 1
    ;;
esac
