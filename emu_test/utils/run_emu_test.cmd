@setlocal enabledelayedexpansion
@echo off

REM This is used to run AVD and console emulator tests.
REM This will be invoked by aosp-emu-master-dev.

set SESSION_DIR=%1

setx PYTEST_ADDOPTS "-m 'not perf'"
echo %PYTEST_ADDOPTS%

if not defined BUILD_TARGET_NAME (
    setx BUILD_TARGET_NAME "unknown-target-windows"
)

prebuilts\python\windows-x86\python.exe external\adt-infra\pytest\test_embedded\run_tests.py --build_dir out\prebuilt_cached\builds --logdir %SESSION_DIR%\testlogs --build_target %BUILD_TARGET_NAME%
if errorlevel 1 (
    echo "Failures during test execution!"
    exit /b 1
)

exit /b 0
