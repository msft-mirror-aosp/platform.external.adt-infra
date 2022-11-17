@setlocal enabledelayedexpansion
@echo off

REM This is used to run AVD and console emulator tests.
REM This will be invoked by aosp-emu-master-dev.

set DISTRIB_DIR=%1

setx ANDROID_HOME %SDK_EMULATOR% /M
setx ANDROID_SDK_ROOT %SDK_EMULATOR% /M
setx ANDROID_EMU_ENABLE_CRASH_REPORTING "YES" /M

call refreshenv

echo "Run mkdir %SESSION_DIR%\emu-master-dev"
set SESSION_DIR=%DISTRIB_DIR%\testlogs
mkdir %SESSION_DIR%
mkdir %SESSION_DIR%\emu-master-dev

set BUILD_DIR=out\prebuilt_cached\builds

echo "Run tar -xf %BUILD_DIR%\sdk-repo-windows-emulator-%BUILD_NUMBER%.zip -C %SESSION_DIR%\emu-master-dev\"
tar -xf %BUILD_DIR%\sdk-repo-windows-emulator-%BUILD_NUMBER%.zip -C %SESSION_DIR%\emu-master-dev\

echo "Run prebuilts\python\windows-x86\python.exe external\adt-infra\pytest\test_embedded\run_tests.py --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --session_dir %SESSION_DIR%"
prebuilts\python\windows-x86\python.exe external\adt-infra\pytest\test_embedded\run_tests.py --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator.exe --session_dir %SESSION_DIR%

echo "Remove deployed emulator"
echo "Run rmdir /s /q %SESSION_DIR%\emu-master-dev"
rmdir /s /q %SESSION_DIR%\emu-master-dev

echo "Cleanup prebuilts"
for /f %%d in ('dir /b C:\buildbot\prebuilt') do (rmdir /s /q C:\buildbot\prebuilt\%%d)

echo "Cleanup empty files"
for /f %%d in ('dir /s /b /A:-D %SESSION_DIR%') do (if %%~zd==0 del %%d)

exit 0
