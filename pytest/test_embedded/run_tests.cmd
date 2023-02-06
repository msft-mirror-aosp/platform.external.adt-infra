@setlocal enabledelayedexpansion
@echo off

REM This is used to run AVD and console emulator tests.
REM This will be invoked by aosp-emu-master-dev.

 %~dp0\..\..\..\..\prebuilts\python\windows-x86\python.exe  %~dp0\run_tests.py %*
if errorlevel 1 (
    echo "Failures during test execution!"
    exit /b 1
)

exit /b 0