@setlocal enabledelayedexpansion
@echo off

:: run adb embedded tests.

title run_adb_test

set DISTRIB_DIR=%1
set AOSP_DIR=%~dp0..\..\..\..\

:: Check if the Distribution dir exists

set "DISTRIB_DIR_EXISTS="
if "%DISTRIB_DIR%" == "" set DISTRIB_DIR_EXISTS=1
if not exist "%DISTRIB_DIR%" set DISTRIB_DIR_EXISTS=1
if defined DISTRIB_DIR_EXISTS (
  echo The variable DISTRIB_DIR points to '%DISTRIB_DIR%', which does not exist.
  exit /b %ERRORLEVEL%
)

:: Check if Python is installed
where python3 >NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo Python interpreter not found.
  exit /b %ERRORLEVEL%
) else (
    python3 --version
)

setx PYTEST_ADDOPTS "-m 'adb'"
call refreshenv

@echo on
python3 -u %AOSP_DIR%\external\adt-infra\pytest\test_embedded\run_tests.py --build_dir out\prebuilt_cached\builds --logdir "%DISTRIB_DIR%\testlogs"

