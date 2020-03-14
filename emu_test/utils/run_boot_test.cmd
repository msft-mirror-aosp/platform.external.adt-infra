@setlocal enabledelayedexpansion
@echo off

REM This is used to run system image BOOT tests.
REM This will be invoked by system image source.
REM {src}/platform_testing/ui_test/run_ui_test.cmd

title run_boot_test

set DISTRIB_DIR=%1
set ORI=%2
set API=%3

setx ANDROID_EMU_ENABLE_CRASH_REPORTING "NO" /M
call refreshenv

set SESSION_DIR=%DISTRIB_DIR%\testlogs
mkdir %SESSION_DIR%

set LOGFILE=%SESSION_DIR%\run_boot_test.log
call :LOG > %LOGFILE% 2>&1
exit 0

:LOG
echo "Runnig BOOT test for %API%"

set FILTER={\"ori\":\"%ORI%\"}

echo "Run python -u %ADT_INFRA%\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %ANDROID_SDK_ROOT%\emulator\emulator --test_dir BOOT_test --file_pattern test_boot.* --config_file %ADT_INFRA%\emu_test\config\boot_cfg_byob.csv --buildername 'Windows_gce' --filter %FILTER% --generate_xml --timeout 900 --headless"
python -u %ADT_INFRA%\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %ANDROID_SDK_ROOT%\emulator\emulator --test_dir BOOT_test --file_pattern test_boot.* --config_file %ADT_INFRA%\emu_test\config\boot_cfg_byob.csv --buildername 'Windows_gce' --filter %FILTER% --generate_xml --timeout 900 --headless

echo "List running processes before killing ADB"
C:\PSTools\tlist.exe /c

echo "Boot test completed, kill adb server"
cmd.exe /c %ANDROID_HOME%\platform-tools\adb.exe kill-server

echo "List running processes after killing ADB"
C:\PSTools\tlist.exe /c

echo "Cleanup empty files"
for /f %%d in ('dir /s /b /A:-D %SESSION_DIR%') do (if %%~zd==0 del %%d)
