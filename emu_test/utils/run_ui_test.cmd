@setlocal enabledelayedexpansion
@echo off

REM This is used to run system image UI tests.
REM This will be invoked by system image source.
REM {src}/platform_testing/ui_test/run_ui_test.cmd

title run_test

set DIST_DIR=%1
set ORI=%2
set API=%3

echo "Running UI test for %API%"

set SNAPSHOT_DIR=%DIST_DIR%\snaps
mkdir %SNAPSHOT_DIR%

set SESSION_DIR=%DIST_DIR%\gtest
mkdir %SESSION_DIR%

for /f %%i in ('dir /b %ANDROID_HOME%\system-images\android-%API%') do (
echo.%%i | findstr /C:"tv" 1>nul && set TARGET=tv && set FILTER={"tag":"android-tv","ori":"%ORI%"} && set TEST_DIR=UI_TEST_tv
echo.%%i | findstr /C:"wear" 1>nul && set TARGET=wear && set FILTER={"tag":"android-wear","ori":"%ORI%"} && set TEST_DIR=UI_TEST_wear
echo.%%i | findstr /C:"playstore" 1>nul && set TARGET=gphone-user && set FILTER={"tag":"google_apis_playstore","ori":"%ORI%"} && set TEST_DIR=UI_TEST_gphone-user

if DEFINED TARGET (
echo "Save snapshots for !TARGET! at %SNAPSHOT_DIR%"
echo "Run python -u %ADT_INFRA%\emu_test\dotest.py --loglevel INFO --session_dir %SESSION_DIR% --emulator %ANDROID_SDK_ROOT%\emulator\emulator --test_dir !TEST_DIR! --file_pattern 'test_ui.*' --config_file %ADT_INFRA%\emu_test\config\ui_cfg_gce.csv --buildername 'Win 8.1 64-bit Quadro 600' --filter !FILTER! --skip-adb-perf --save_snapshot"
python -u %ADT_INFRA%\emu_test\dotest.py --loglevel INFO --session_dir %SESSION_DIR% --emulator %ANDROID_SDK_ROOT%\emulator\emulator --test_dir !TEST_DIR! --file_pattern 'test_ui.*' --config_file %ADT_INFRA%\emu_test\config\ui_cfg_gce.csv --buildername 'Win 8.1 64-bit Quadro 600' --filter !FILTER! --skip-adb-perf --save_snapshot

echo "Use Snapshots for !TARGET! from %SNAPSHOT_DIR%"
echo "Run tests on !TARGET!"
echo "Run python -u %ADT_INFRA%\emu_test\dotest.py --loglevel INFO --session_dir %SESSION_DIR% --emulator %ANDROID_SDK_ROOT%\emulator\emulator --test_dir !TEST_DIR! --file_pattern 'test_ui.*' --config_file %ADT_INFRA%\emu_test\config\ui_cfg_gce.csv --buildername 'Win 8.1 64-bit Quadro 600' --filter !FILTER! --skip-adb-perf --load_snapshot"
python -u %ADT_INFRA%\emu_test\dotest.py --loglevel INFO --session_dir %SESSION_DIR% --emulator %ANDROID_SDK_ROOT%\emulator\emulator --test_dir !TEST_DIR! --file_pattern 'test_ui.*' --config_file %ADT_INFRA%\emu_test\config\ui_cfg_gce.csv --buildername 'Win 8.1 64-bit Quadro 600' --filter !FILTER! --skip-adb-perf --load_snapshot
)

set TARGET=
set FILTER=
set TEST_DIR=
)

rmdir /s /q %SNAPSHOT_DIR%
