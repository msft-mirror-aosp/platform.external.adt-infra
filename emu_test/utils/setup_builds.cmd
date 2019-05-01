@setlocal enabledelayedexpansion
@echo off

REM This is used to setup system image builds.
REM This will be invoked by system image source.
REM {src}/platform_testing/ui_test/run_test.cmd

set BUILD_DIR=%1
set API=%2

REM echo "Update SDK"
REM echo "Run %ANDROID_HOME%\tools\bin\sdkmanager.bat --update"
REM cmd.exe /c yes | %ANDROID_HOME%\tools\bin\sdkmanager.bat --licenses
REM cmd.exe /c %ANDROID_HOME%\tools\bin\sdkmanager.bat --update

rmdir /s /q %ANDROID_HOME%\system-images\android-%API%
mkdir %ANDROID_HOME%\system-images\android-%API%

echo "Copy and extract builds"
for /f %%i in ('dir /b %BUILD_DIR%') do (
set IMAGE_TYPE=google_apis

echo.%%i | findstr /C:"tv" 1>nul && set IMAGE_TYPE=android-tv
echo.%%i | findstr /C:"wear" 1>nul && set IMAGE_TYPE=android-wear
echo.%%i | findstr /C:"user" 1>nul && set IMAGE_TYPE=google_apis_playstore

echo "Run mkdir %ANDROID_HOME%\system-images\android-%API%\!IMAGE_TYPE!"
mkdir %ANDROID_HOME%\system-images\android-%API%\!IMAGE_TYPE!

echo "7z x -aoa %BUILD_DIR%\%%i\* -o%ANDROID_HOME%\system-images\android-%API%\!IMAGE_TYPE!"
7z x -aoa %BUILD_DIR%\%%i\* -o%ANDROID_HOME%\system-images\android-%API%\!IMAGE_TYPE!
)

echo "setup complete"
