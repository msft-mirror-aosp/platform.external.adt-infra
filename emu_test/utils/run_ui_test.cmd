@setlocal enabledelayedexpansion
@echo off

REM This is used to run system image UI tests.
REM This will be invoked by system image source.
REM {src}/platform_testing/ui_test/run_ui_test.cmd

title run_ui_test

set DISTRIB_DIR=%1
set ORI=%2
set API=%3

setx ANDROID_EMU_ENABLE_CRASH_REPORTING "NO" /M
call refreshenv

set SNAPSHOT_DIR=%DISTRIB_DIR%\snaps
mkdir %SNAPSHOT_DIR%

set SESSION_DIR=%DISTRIB_DIR%\testlogs
mkdir %SESSION_DIR%

set LOGFILE=%SESSION_DIR%\run_ui_test.log
call :LOG > %LOGFILE% 2>&1
exit 0

:LOG
echo "Running UI test for %API%"

for /f %%i in ('dir /b %ANDROID_HOME%\system-images\android-%API%') do (
echo.%%i | findstr /C:"tv" 1>nul && set TARGET=tv && set FILTER={\"tag\":\"android-tv\",\"ori\":\"%ORI%\"} && set TEST_DIR=UI_TEST_tv
echo.%%i | findstr /C:"wear" 1>nul && set TARGET=wear && set FILTER={\"tag\":\"android-wear\",\"ori\":\"%ORI%\"} && set TEST_DIR=UI_TEST_wear
echo.%%i | findstr /C:"playstore" 1>nul && set TARGET=gphone-user && set FILTER={\"tag\":\"google_apis_playstore\",\"ori\":\"%ORI%\"} && set TEST_DIR=UI_TEST_gphone-user

if DEFINED TARGET (
echo "Save snapshots for !TARGET! at %SNAPSHOT_DIR%"
echo "Run python -u %ADT_INFRA%\emu_test\dotest.py --loglevel INFO --session_dir %SESSION_DIR% --emulator %ANDROID_SDK_ROOT%\emulator\emulator-headless --test_dir !TEST_DIR! --file_pattern test_ui.* --config_file %ADT_INFRA%\emu_test\config\ui_cfg_byob.csv --buildername Windows_gce --filter !FILTER! --skip-adb-perf --save_snapshot --timeout 900"
python -u %ADT_INFRA%\emu_test\dotest.py --loglevel INFO --session_dir %SESSION_DIR% --emulator %ANDROID_SDK_ROOT%\emulator\emulator-headless --test_dir !TEST_DIR! --file_pattern test_ui.* --config_file %ADT_INFRA%\emu_test\config\ui_cfg_byob.csv --buildername Windows_gce --filter !FILTER! --skip-adb-perf --save_snapshot --timeout 900

rmdir /s /q %SESSION_DIR%\!TEST_DIR!

echo "Use Snapshots for !TARGET! from %SNAPSHOT_DIR%"
echo "Run tests on !TARGET!"
echo "Run python -u %ADT_INFRA%\emu_test\dotest.py --loglevel INFO --session_dir %SESSION_DIR% --emulator %ANDROID_SDK_ROOT%\emulator\emulator-headless --test_dir !TEST_DIR! --file_pattern test_ui.* --config_file %ADT_INFRA%\emu_test\config\ui_cfg_byob.csv --buildername Windows_gce --filter !FILTER! --skip-adb-perf --load_snapshot --timeout 900"
python -u %ADT_INFRA%\emu_test\dotest.py --loglevel INFO --session_dir %SESSION_DIR% --emulator %ANDROID_SDK_ROOT%\emulator\emulator-headless --test_dir !TEST_DIR! --file_pattern test_ui.* --config_file %ADT_INFRA%\emu_test\config\ui_cfg_byob.csv --buildername Windows_gce --filter !FILTER! --skip-adb-perf --load_snapshot --timeout 900
)

set TARGET=
set FILTER=
set TEST_DIR=
)

echo "rmdir /s /q %SNAPSHOT_DIR%"
rmdir /s /q %SNAPSHOT_DIR%

echo "List running processes before killing ADB"
C:\PSTools\tlist.exe /c

echo "UI test completed, kill adb server"
cmd.exe /c %ANDROID_HOME%\platform-tools\adb.exe kill-server
python -u %ADT_INFRA%\emu_test\utils\kill_android_bridge_server.py

echo "List running processes after killing ADB"
C:\PSTools\tlist.exe /c

echo "Cleanup empty files"
for /f %%d in ('dir /s /b /A:-D %SESSION_DIR%') do (if %%~zd==0 del %%d)
