@echo off
REM Runs the named snapshot ETS sequence (@goldfish_test//ets/snapshot:named_snapshot) locally on
REM Windows the way run_local.sh does on gLinux and macOS (android_ets_cfg.py): builds the emulator
REM from this checkout, cold boots it on the same system image with the same AVD, flags and device
REM setup, runs NamedSnapshotTest and AdbEmuSnapshotTest (snapshot_phase=cold_boot), closes it with
REM CloseEmulatorTest (which saves default_boot), relaunches it with "-snapshot ets_named" (the
REM snapshot NamedSnapshotTest created over gRPC), runs the modules again with
REM snapshot_phase=load_1 and closes it again.
REM
REM Set ETS_NO_SNAPSHOT=1 to run the named_snapshot_disabled variant instead: a single cold boot
REM with -no-snapshot, where only the -no-snapshot rejections of NamedSnapshotTest apply.
REM Extra arguments are passed on to Tradefed, e.g.
REM   run_local.bat --module-arg NamedSnapshotTest:set-option:snapshots_disabled:true
REM Set EMULATOR_PORT to pick the console port instead of the first free one.
REM
REM The emulator logs, a screen recording of the guest for every phase (video\<phase>_*.mp4, taken
REM with adb screenrecord so that no UI is needed) and the Tradefed logs and results are written to
REM out\ets_snapshot\<timestamp> under the repo root and, like run_local.sh's, reported to Sponge
REM (see ets\ui\report_to_sponge.bat).
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "UI_DIR=%SCRIPT_DIR%..\ui\"
for %%I in ("%SCRIPT_DIR%..\..\..\..\..") do set "REPO_ROOT=%%~fI"
set "BAZEL=%REPO_ROOT%\prebuilts\bazel\windows-x86_64\bazel.exe"
REM @goldfish//emulator/libs/grpc_security:unsecure-emulator-access, the allowlist the sequence uses.
set "ALLOWLIST=%REPO_ROOT%\hardware\generic\goldfish\emulator\libs\grpc_security\testdata\test_allow_list.json"
REM The snapshot NamedSnapshotTest.namedSnapshotSurvivesRelaunch creates in cold_boot and the
REM relaunch boots from (NamedSnapshotTest.RELAUNCH_SNAPSHOT, --relaunch_emulator_args in BUILD.bazel).
set "RELAUNCH_SNAPSHOT=ets_named"

REM The emulator and Tradefed look for adb on PATH; Tradefed also needs java.
where adb >nul 2>&1 || (
  for %%A in ("%ANDROID_SDK_ROOT%\platform-tools" "%LOCALAPPDATA%\Android\Sdk\platform-tools" "%REPO_ROOT%\prebuilts\android\android-sdk\windows\platform-tools") do (
    if not defined ADB_DIR if exist "%%~A\adb.exe" set "ADB_DIR=%%~A"
  )
  if not defined ADB_DIR (
    echo adb not found. Add platform-tools to PATH or set ANDROID_SDK_ROOT.
    exit /b 1
  )
  set "PATH=!ADB_DIR!;!PATH!"
)
where java >nul 2>&1 || (
  echo java not found. Tradefed needs Java 17 or newer on PATH.
  exit /b 1
)

REM Boot on the first free console port like the sequencer does, unless EMULATOR_PORT is set.
if not defined EMULATOR_PORT for /f %%P in ('powershell -NoProfile -Command "for ($p = 5554; $p -le 5682; $p += 2) { $free = $true; foreach ($q in $p, ($p + 1)) { try { $l = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $q); $l.Start(); $l.Stop() } catch { $free = $false } }; if ($free) { $p; break } }"') do set "EMULATOR_PORT=%%P"
if not defined EMULATOR_PORT (
  echo No free emulator console port found between 5554 and 5682.
  exit /b 1
)
set "SERIAL=emulator-%EMULATOR_PORT%"

REM Like the goldfish_fetch, tradefed_fetch and avd steps: build an optimized emulator and the ETS
REM from this checkout and fetch the system image the sequence boots on gLinux. The outputs live
REM under configuration specific directories, so ask bazel where they are instead of going through
REM bazel-bin. See ets\ui\run_external.bat for why the ETS may need its own shell and output dir.
set "ETS_BAZEL_FLAGS="
set "ETS_BUSYBOX_SH="
if defined BAZEL_SH if /i not "!BAZEL_SH:busybox=!"=="!BAZEL_SH!" set "ETS_BUSYBOX_SH=1"
if defined ETS_BUSYBOX_SH (
  for %%B in ("%ProgramFiles%\Git\usr\bin\bash.exe" "%ProgramFiles%\Git\bin\bash.exe" "%LOCALAPPDATA%\Programs\Git\usr\bin\bash.exe" "C:\msys64\usr\bin\bash.exe") do (
    if not defined ETS_BASH if exist "%%~B" set "ETS_BASH=%%~B"
  )
  if defined ETS_BASH (
    echo BAZEL_SH is busybox, which cannot run the unzip script and commands rules_android uses. Building the ETS with !ETS_BASH! instead.
    set "ETS_BAZEL_FLAGS="--shell_executable=!ETS_BASH!" "--repo_env=BAZEL_SH=!ETS_BASH!" "--experimental_override_name_platform_in_output_dir=@goldfish_build//platforms:windows_x64=ets""
  ) else (
    echo WARNING: BAZEL_SH is busybox and no Git Bash or MSYS2 bash was found. The ETS build may fail with "unzip: Exec format error".
  )
)
echo === Building the emulator and the ETS, fetching the system image
pushd "%REPO_ROOT%"
"%BAZEL%" build -c opt @goldfish//emulator:release @goldfish_test//ets/snapshot:system_image
if errorlevel 1 (
  popd
  exit /b 1
)
"%BAZEL%" build %ETS_BAZEL_FLAGS% @goldfish_test//ets:android_ets_zip
if errorlevel 1 (
  popd
  exit /b 1
)
for /f "delims=" %%I in ('call "%BAZEL%" info execution_root 2^>nul') do set "EXEC_ROOT=%%I"
for /f "delims=" %%I in ('call "%BAZEL%" info output_base 2^>nul') do set "OUTPUT_BASE=%%I"
for /f "delims=" %%F in ('call "%BAZEL%" cquery -c opt --output=files @goldfish//emulator:release 2^>nul') do set "EMULATOR_ZIP=%EXEC_ROOT%/%%F"
for /f "delims=" %%F in ('call "%BAZEL%" cquery %ETS_BAZEL_FLAGS% --output=files @goldfish_test//ets:android_ets_zip 2^>nul') do set "ETS_ZIP=%EXEC_ROOT%/%%F"
for /f "delims=" %%F in ('call "%BAZEL%" cquery -c opt --output=files @goldfish_test//ets/snapshot:system_image 2^>nul') do (
  set "LINE=%%F"
  if /i "!LINE:~-11!"=="/system.img" set "SYSTEM_IMG=%OUTPUT_BASE%/%%F"
)
popd
if not defined EMULATOR_ZIP (
  echo Could not locate the output of @goldfish//emulator:release with bazel cquery.
  exit /b 1
)
if not defined ETS_ZIP (
  echo Could not locate the output of @goldfish_test//ets:android_ets_zip with bazel cquery.
  exit /b 1
)
if not defined SYSTEM_IMG (
  echo Could not locate system.img in @goldfish_test//ets/snapshot:system_image with bazel cquery.
  exit /b 1
)
set "EMULATOR_ZIP=%EMULATOR_ZIP:/=\%"
set "ETS_ZIP=%ETS_ZIP:/=\%"
set "SYSTEM_IMG=%SYSTEM_IMG:/=\%"
for %%F in ("%SYSTEM_IMG%") do set "SYSDIR=%%~dpF"

set "WORK_DIR=%TEMP%\ets_snapshot_%RANDOM%"
mkdir "%WORK_DIR%\avd\ets.avd"
mkdir "%WORK_DIR%\ets"
echo === Extracting %EMULATOR_ZIP% and %ETS_ZIP% into %WORK_DIR%
"%SystemRoot%\System32\tar.exe" -xf "%EMULATOR_ZIP%" -C "%WORK_DIR%"
if not exist "%WORK_DIR%\emulator\emulator.exe" (
  echo Could not extract the emulator.
  rmdir /s /q "%WORK_DIR%"
  exit /b 1
)
powershell -NoProfile -Command "Expand-Archive -Path '%ETS_ZIP%' -DestinationPath '%WORK_DIR%\ets' -Force"
set "ETS_TRADEFED=%WORK_DIR%\ets\android-ets\tools\ets-tradefed.bat"
if not exist "%ETS_TRADEFED%" (
  echo Could not extract the ETS.
  rmdir /s /q "%WORK_DIR%"
  exit /b 1
)

REM The AVD agent_common.avd_ets creates: a UTF-8 display name and 8G of RAM.
set "ANDROID_AVD_HOME=%WORK_DIR%\avd"
> "%ANDROID_AVD_HOME%\ets.ini" echo path=%ANDROID_AVD_HOME%\ets.avd
powershell -NoProfile -Command "[IO.File]::WriteAllLines('%ANDROID_AVD_HOME%\ets.avd\config.ini', @(('avd.ini.displayname=UTF8' + [char]::ConvertFromUtf32(0x1F916)), 'hw.ramSize=8192', 'image.sysdir.1=%SYSDIR%'))"

for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "OUT_DIR=%REPO_ROOT%\out\ets_snapshot\%%T"
mkdir "%OUT_DIR%\video"

REM Matches the emulator launcher and its QEMU process, but not helpers such as netsimd, which
REM can be shared with other emulators and outlive this one.
set "EMU_PROCS=Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '%WORK_DIR%\emulator\*' -and ($_.Name -eq 'emulator.exe' -or $_.Name -like 'qemu-system-*') }"
REM Like the goldfish_grpc step: the same emulator flags for every launch.
set "BASE_ARGS=-avd ets -port %EMULATOR_PORT% -verbose -show-kernel -qt-hide-window -not-in-bazel -verbose-grpc -grpc-allowlist "%ALLOWLIST%""
REM The Tradefed arguments agent_common.ets passes, plus the module of the named_snapshot plans.
set "TF_ARGS=run commandAndExit ets --abi x86_64 --retry-strategy RETRY_ANY_FAILURE --max-testcase-run-count 3 -s %SERIAL% --include-filter NamedSnapshotTest --include-filter AdbEmuSnapshotTest"

if defined ETS_NO_SNAPSHOT (
  REM named_snapshot_disabled: one cold boot with -no-snapshot; the test asserts the rejections.
  set "PHASES=cold_boot"
  set "LAUNCH_ARGS_cold_boot=-no-snapshot"
  set "TF_EXTRA_cold_boot=--module-arg NamedSnapshotTest:set-option:snapshots_disabled:true"
  set "EXPECTED_RESULTS=2"
) else (
  REM named_snapshot: cold boot, then relaunch from the snapshot created over gRPC.
  set "PHASES=cold_boot load_1"
  set "LAUNCH_ARGS_cold_boot="
  set "LAUNCH_ARGS_load_1=-snapshot %RELAUNCH_SNAPSHOT%"
  set "TF_EXTRA_cold_boot="
  set "TF_EXTRA_load_1="
  set "EXPECTED_RESULTS=4"
)

set "EXIT_CODE=0"
REM One iteration per phase (cold_boot, then load_1 booted from the named snapshot): boot the
REM emulator, record its screen, run the module with snapshot_phase=<phase>, then close it with
REM CloseEmulatorTest (which saves the snapshot the emulator was launched with).
REM (Inline rather than "call :label": cmd can fail to find labels in a .bat with LF line endings.)
for %%P in (%PHASES%) do if "!EXIT_CODE!"=="0" (
  set "PHASE=%%P"
  set "PHASE_LAUNCH_ARGS=!LAUNCH_ARGS_%%P!"
  set "PHASE_TF_EXTRA=!TF_EXTRA_%%P!"
  set "REC_STOP=%WORK_DIR%\stop_recording_%%P"
  set "BOOTED=0"
  echo === [%%P] Booting %SERIAL%: emulator.exe %BASE_ARGS% !PHASE_LAUNCH_ARGS!
  echo     log: %OUT_DIR%\emulator_%%P.log
  start "" /b "%WORK_DIR%\emulator\emulator.exe" %BASE_ARGS% !PHASE_LAUNCH_ARGS! > "%OUT_DIR%\emulator_%%P.log" 2>&1
  powershell -NoProfile -Command "$end = (Get-Date).AddMinutes(10); while ((Get-Date) -lt $end) { if (((adb -s %SERIAL% shell getprop sys.boot_completed 2>$null) -join '').Trim() -eq '1') { exit 0 }; if (-not (%EMU_PROCS%)) { exit 2 }; Start-Sleep -Seconds 2 }; exit 1"
  if errorlevel 1 (
    echo [%%P] The emulator did not boot, see %OUT_DIR%\emulator_%%P.log
    set "EXIT_CODE=1"
  ) else (
    set "BOOTED=1"
  )

  if "!BOOTED!"=="1" (
    if "%%P"=="cold_boot" (
      REM The same device setup android_ets_cfg.py applies before running the tests. Only needed
      REM once: a snapshot boot resumes the already set up guest.
      echo === [%%P] Setting up %SERIAL%
      for %%C in (
        "settings put global device_provisioned 1"
        "settings put secure user_setup_complete 1"
        "pm disable-user --user 0 com.android.vending"
        "pm disable-user --user 0 com.google.android.configupdater"
        "pm disable-user --user 0 com.google.android.gms"
        "pm disable-user --user 0 com.google.android.gsf"
        "am force-stop com.android.settings"
        "am force-stop com.google.android.bluetooth"
        "am force-stop com.android.phone"
        "am force-stop com.google.android.gms"
        "settings put global hide_error_dialogs 1"
        "settings put global window_animation_scale 0.0"
        "settings put global transition_animation_scale 0.0"
        "settings put global animator_duration_scale 0.0"
        "am kill-all"
        "am wait-for-broadcast-barrier"
        "am wait-for-broadcast-idle"
      ) do adb -s %SERIAL% shell %%~C
    )

    REM Record the guest screen for the whole phase, without any UI. screenrecord stops after 3
    REM minutes, so record consecutive segments until the stop file appears, pulling each one into
    REM OUT_DIR\video.
    start "" /b powershell -NoProfile -Command "$i = 0; while (-not (Test-Path '!REC_STOP!')) { $i++; $dev = '/sdcard/ets_%%P_' + $i + '.mp4'; adb -s %SERIAL% shell screenrecord --time-limit 180 --bit-rate 2000000 $dev 2>$null | Out-Null; adb -s %SERIAL% pull $dev ('%OUT_DIR%\video\%%P_' + $i + '.mp4') 2>$null | Out-Null; adb -s %SERIAL% shell rm -f $dev 2>$null | Out-Null }" > "%OUT_DIR%\video\%%P_recording.log" 2>&1

    echo === [%%P] Running NamedSnapshotTest and AdbEmuSnapshotTest on %SERIAL% (snapshot_phase=%%P)
    pushd "%REPO_ROOT%"
    call "%ETS_TRADEFED%" %TF_ARGS% --suite-name ETS_%%P --module-arg NamedSnapshotTest:set-option:snapshot_phase:%%P !PHASE_TF_EXTRA! %*
    popd

    REM Stop the recording: the stop file ends the loop, interrupting screenrecord finishes the
    REM current segment so that it is pulled.
    type nul > "!REC_STOP!"
    adb -s %SERIAL% shell pkill -INT screenrecord >nul 2>&1
    powershell -NoProfile -Command "Start-Sleep -Seconds 5"

    REM The ets_close step: CloseEmulatorTest shuts the emulator down over gRPC, which saves the
    REM snapshot it was launched with, and checks that it and netsimd exit.
    echo === [%%P] Closing %SERIAL%
    pushd "%REPO_ROOT%"
    call "%ETS_TRADEFED%" run commandAndExit ets -m CloseEmulatorTest --suite-name ETS-CLOSE_%%P --abi x86_64 --null-device --module-arg=CloseEmulatorTest:set-option:emu_serial:%SERIAL%
    popd
  )

  REM Give the emulator two minutes to exit, it saves its snapshot first, then stop whatever is
  REM left of this install.
  powershell -NoProfile -Command "$end = (Get-Date).AddMinutes(2); while ((Get-Date) -lt $end -and (%EMU_PROCS%)) { Start-Sleep -Seconds 1 }; Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '%WORK_DIR%\emulator\*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
  if not exist "!REC_STOP!" type nul > "!REC_STOP!"
  REM Keep a listing of the per-snapshot metadata after this phase next to the logs: it shows what
  REM the emulator and QEMU wrote under <avd>\snapshots\<name>\: version.txt and renderer\.
  powershell -NoProfile -Command "if (Test-Path '%ANDROID_AVD_HOME%\ets.avd\snapshots') { Get-ChildItem -Recurse '%ANDROID_AVD_HOME%\ets.avd\snapshots' | ForEach-Object { $_.FullName.Substring('%ANDROID_AVD_HOME%\ets.avd\'.Length) } | Out-File -Encoding utf8 '%OUT_DIR%\snapshots_after_%%P.txt' }"
)


REM Tradefed's exit code is meaningless (see ets\ui\run_external.bat): require the results of every
REM invocation (tests and CloseEmulatorTest of each phase) to be present and passed.
powershell -NoProfile -ExecutionPolicy Bypass -File "%UI_DIR%check_tradefed_results.ps1" "%WORK_DIR%\ets\android-ets\results" %EXPECTED_RESULTS%
if errorlevel 1 set "EXIT_CODE=1"

REM Keep the test outputs like bazel-testlogs does on Linux and macOS.
if exist "%WORK_DIR%\ets\android-ets\logs" robocopy "%WORK_DIR%\ets\android-ets\logs" "%OUT_DIR%\logs" /E >nul
if exist "%WORK_DIR%\ets\android-ets\results" robocopy "%WORK_DIR%\ets\android-ets\results" "%OUT_DIR%\results" /E >nul
rmdir /s /q "%WORK_DIR%"

REM run_local.sh is a Bazel test, so Bazel reports it to Sponge. Report this run the same way (every
REM Tradefed invocation, the emulator logs, the screen recordings and the snapshot listings); see
REM ets\ui\report_to_sponge.bat. The verdict above does not depend on this step.
echo === Reporting the results to Sponge
call "%UI_DIR%report_to_sponge.bat" "%OUT_DIR%" %EXPECTED_RESULTS%
echo Emulator logs, screen recordings and test outputs: %OUT_DIR%
exit /b %EXIT_CODE%
