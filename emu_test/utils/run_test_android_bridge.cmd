@setlocal enabledelayedexpansion
@echo off

REM This is used to run ADB tests.
REM This will be invoked by system image source.
REM {src}/platform_testing/emu_test/run_test.cmd

title run_test_android_bridge

set DISTRIB_DIR=%1

setx ANDROID_EMU_ENABLE_CRASH_REPORTING "NO" /M

call refreshenv

set SESSION_DIR=%DISTRIB_DIR%\testlogs
mkdir %SESSION_DIR%

set GENERAL_TESTS_DIR=%DISTRIB_DIR%\general-tests\host\testcases

set LOGFILE=%SESSION_DIR%\run_test_android_bridge.log
call :LOG > %LOGFILE% 2>&1
exit 0

:LOG
start cmd /c "title test_timer & python -u external\adt-infra\emu_test\utils\test_timer.py --timeout 5400"
echo "Run python -u %ADT_INFRA%\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %ANDROID_SDK_ROOT%\emulator\emulator --test_dir ADB_test --file_pattern test_adb.* --config_file %ADT_INFRA%\emu_test\config\adb_cfg_byob.csv --buildername Windows_gce --filter {\"ori\":\"public\"} --timeout 900 --headless"
python -u %ADT_INFRA%\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %ANDROID_SDK_ROOT%\emulator\emulator --test_dir ADB_test --file_pattern test_adb.* --config_file %ADT_INFRA%\emu_test\config\adb_cfg_byob.csv --buildername Windows_gce --filter {\"ori\":\"public\"} --timeout 900 --headless
tasklist /v | find "test_timer"
if errorlevel 1 goto ADBTimeOut
taskkill /fi "windowtitle eq Administrator:  test_timer*"
goto ADBDone

:ADBTimeOut
echo "ADB test timed out"

:ADBDone
echo "List running processes before killing ADB"
C:\PSTools\tlist.exe /c

echo "ADB test completed, kill adb server"
cmd.exe /c %ANDROID_HOME%\platform-tools\adb.exe kill-server
python -u %ADT_INFRA%\emu_test\utils\kill_android_bridge_server.py

echo "List running processes after killing ADB"
C:\PSTools\tlist.exe /c

echo "Cleanup empty files"
for /f %%d in ('dir /s /b /A:-D %SESSION_DIR%') do (if %%~zd==0 del %%d)

echo "ADB test completed"
