@setlocal enabledelayedexpansion
@echo off

REM This is used to run AVD and console emulator tests.
REM This will be invoked by aosp-emu-master-dev.

set DISTRIB_DIR=%1

setx ANDROID_HOME "%SDK_EMULATOR%" /M
setx ANDROID_SDK_ROOT "%SDK_EMULATOR%" /M
setx ANDROID_EMU_ENABLE_CRASH_REPORTING "YES" /M
REM If JAVA_HOME was set in the local environment, we want that to make it through the refreshenv
setx JAVA_HOME "%JAVA_HOME%" /M

call refreshenv
IF "%JAVA_HOME%"=="" (
    REM Building the test apk needed for the tests will silently fail somewhere in python without JAVA_HOME
    ECHO JAVA_HOME must be set in order for the test apk to get built
    exit 255
)

IF "%ANDROID_SDK_ROOT%"=="" (
    REM Building the test apk needed for the tests will silently fail somewhere in python without JAVA_HOME
    ECHO "SDK_EMULATOR must be set in order for the test apk to get built (typically prebuilts/android-emulator-build/system-images/windows)"
    exit 255
)

echo "Run mkdir %SESSION_DIR%\emu-master-dev"
set SESSION_DIR=%DISTRIB_DIR%\testlogs
mkdir %SESSION_DIR%
mkdir %SESSION_DIR%\emu-master-dev

set BUILD_DIR=out\prebuilt_cached\builds

echo "Run tar -xf %BUILD_DIR%\sdk-repo-windows-emulator-%BUILD_NUMBER%.zip -C %SESSION_DIR%\emu-master-dev\"
tar -xf %BUILD_DIR%\sdk-repo-windows-emulator-%BUILD_NUMBER%.zip -C %SESSION_DIR%\emu-master-dev\

echo "Run prebuilts\python\windows-x86\python.exe external\adt-infra\pytest\test_embedded\run_tests.py --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --session_dir %SESSION_DIR%"
prebuilts\python\windows-x86\python.exe external\adt-infra\pytest\test_embedded\run_tests.py --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator.exe --session_dir %SESSION_DIR%  --logdir $SESSION_DIR/testlogs
set TEST_EXIT=%error_level%  --logdir $SESSION_DIR/testlogs

echo "Remove deployed emulator"
echo "Run rmdir /s /q %SESSION_DIR%\emu-master-dev"
rmdir /s /q %SESSION_DIR%\emu-master-dev

echo "Cleanup prebuilts"
for /f %%d in ('dir /b C:\buildbot\prebuilt') do (rmdir /s /q C:\buildbot\prebuilt\%%d)

echo "Cleanup empty files"
for /f %%d in ('dir /s /b /A:-D %SESSION_DIR%') do (if %%~zd==0 del %%d)

exit /b %TEST_EXIT%
