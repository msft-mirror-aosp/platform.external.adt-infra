@setlocal enabledelayedexpansion
@echo off

REM This is used to run AVD and console emulator tests.
REM This will be invoked by aosp-emu-master-dev.

set SESSION_DIR=%1

prebuilts\python\windows-x86\python.exe external\adt-infra\pytest\test_embedded\run_tests.py --build_dir out\prebuilt_cached\builds --logdir %SESSION_DIR%\logdir
if errorlevel 1 (
    echo "Failures during test execution!"
    exit /b 1
)

exit /b 0