# ETS snapshot tests

Host tests of the emulator's snapshot support, run by Tradefed against a booted emulator.

| Module | What it checks |
| :--- | :--- |
| `SnapshotVersionTest` | `<avd>/snapshots/default_boot/version.txt` gates the Quickboot load: matching version loads, a mismatch cold boots. |
| `AdbEmuSnapshotTest` | `adb emu avd snapshot save\|load\|del\|list` (the console, through the legacy `SnapshotService`): a snapshot saved by name gets its directory, loads back and is removed by `del`; bad arguments and `-no-snapshot` are rejected. |
| `NamedSnapshotTest` | Snapshots saved under a name at runtime through `HypervisorService` v2: create / list / restore / delete, incompatible and invalid snapshots are rejected, `-no-snapshot` rejects save and load, and a relaunch with `-snapshot <name>` resumes from a snapshot created over gRPC. |

Every snapshot owns `<avd>/snapshots/<name>/` (`version.txt` written by the emulator, `renderer/`
written by QEMU's virtio-gpu-rutabaga device) next to the qcow2 internal snapshot tagged `<name>`.

## Running

gLinux and macOS (Bazel test, reported to Sponge):

```sh
third_party/adt-infra/goldfish_test/ets/snapshot/run_local.sh             # :named_snapshot
third_party/adt-infra/goldfish_test/ets/snapshot/run_local.sh --disabled  # :named_snapshot_disabled
bazel test --config=remote --strategy=TestRunner=local @goldfish_test//ets/snapshot:snapshot
```

Windows (outside Bazel, same emulator build, flags and device setup; reported to Sponge through
`ets\ui\report_to_sponge.bat`):

```bat
third_party\adt-infra\goldfish_test\ets\snapshot\run_local.bat
set ETS_NO_SNAPSHOT=1 && third_party\adt-infra\goldfish_test\ets\snapshot\run_local.bat
```

`run_local.bat` boots the emulator, records the guest screen with `adb screenrecord`, runs
`NamedSnapshotTest` and `AdbEmuSnapshotTest`, closes the emulator with `CloseEmulatorTest`, relaunches it with
`-snapshot ets_named` and repeats with `snapshot_phase=load_1`. Emulator logs, the recordings
(`video\<phase>_<n>.mp4`), a listing of `<avd>\snapshots` after each phase and the Tradefed logs
and results are written to `out\ets_snapshot\<timestamp>` and uploaded to Sponge.

The plans use the sequence flags `--emulator_args` (every launch) and `--relaunch_emulator_args`
(relaunches only); see `ets/snapshot/BUILD.bazel`.
