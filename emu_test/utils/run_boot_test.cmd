@setlocal enabledelayedexpansion
@echo off

REM This is used to run system image BOOT tests.
REM This will be invoked by system image source.
REM {src}/platform_testing/ui_test/run_ui_test.cmd

title run_test

set DIST_DIR=%1
set ORI=%2
set API=%3

echo "Runnig BOOT test for %API%"

set SESSION_DIR=%DIST_DIR%\gtest
mkdir %SESSION_DIR%

set FILTER={"ori":"%ORI%"}

echo "Run python -u %ADT_INFRA%\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %ANDROID_SDK_ROOT%\emulator\emulator --test_dir BOOT_test --file_pattern 'test_boot.*' --config_file %ADT_INFRA%\emu_test\config\boot_cfg_gce.csv --buildername 'Win 7 64-bit HD 4400' --filter %FILTER%"
python -u %ADT_INFRA%\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %ANDROID_SDK_ROOT%\emulator\emulator --test_dir BOOT_test --file_pattern 'test_boot.*' --config_file %ADT_INFRA%\emu_test\config\boot_cfg_gce.csv --buildername 'Win 7 64-bit HD 4400' --filter %FILTER%
