@setlocal enabledelayedexpansion
@echo off

REM This is used to run AVD and console emulator tests.
REM This will be invoked by aosp-emu-master-dev.

set DIST_DIR=%1

setx ANDROID_HOME %SDK_EMULATOR% /M
setx ANDROID_SDK_ROOT %SDK_EMULATOR% /M

call refreshenv

set SESSION_DIR=%DIST_DIR%\testlogs
mkdir %SESSION_DIR%

echo "Deploy emulator"
echo "Run mkdir %SESSION_DIR%\emu-master-dev"
mkdir %SESSION_DIR%\emu-master-dev

set BUILD_DIR=C:\buildbot\prebuilt\%BUILD_NUMBER%\sdk_tools_linux

echo "Run 7z x -aoa %BUILD_DIR%\sdk-repo-windows-emulator-*.zip -o%SESSION_DIR%\emu-master-dev"
7z x -aoa %BUILD_DIR%\sdk-repo-windows-emulator-*.zip -o%SESSION_DIR%\emu-master-dev

echo "Update SDK"
echo "Run %ANDROID_HOME%\tools\bin\sdkmanager.bat --update"
cmd.exe /c yes | %ANDROID_HOME%\tools\bin\sdkmanager.bat --licenses
cmd.exe /c %ANDROID_HOME%\tools\bin\sdkmanager.bat --update

echo "Running Boot tests"
echo "Run python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir BOOT_test --file_pattern test_boot.* --config_file external\adt-infra\emu_test\config\boot_cfg_byob.csv --buildername 'Windows_gce' --filter {\"ori\":\"public\"} --timeout 900 --generate_xml"
python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir BOOT_test --file_pattern test_boot.* --config_file external\adt-infra\emu_test\config\boot_cfg_byob.csv --buildername 'Windows_gce' --filter {\"ori\":\"public\"} --timeout 900 --generate_xml

REM echo "Running AVD tests"
REM echo "Run python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir AVD_test --file_pattern *launch_avd*.* --config_file external\adt-infra\emu_test\config\avd_cfg_byob.csv --buildername 'Windows_gce' --skip-adb-perf --timeout 900 --generate_xml"
REM python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir AVD_test --file_pattern *launch_avd*.* --config_file external\adt-infra\emu_test\config\avd_cfg_byob.csv --buildername 'Windows_gce' --skip-adb-perf --timeout 900 --generate_xml

echo "Running Console tests"
echo "Run python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir Console_test --file_pattern test_console.* --config_file external\adt-infra\emu_test\config\console_cfg_byob.csv --buildername 'Windows_gce' --skip-adb-perf --timeout 900"
python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir Console_test --file_pattern test_console.* --config_file external\adt-infra\emu_test\config\console_cfg_byob.csv --buildername 'Windows_gce' --skip-adb-perf --timeout 900

echo "Remove deployed emulator"
echo "Run rmdir /s /q %SESSION_DIR%\emu-master-dev"
rmdir /s /q %SESSION_DIR%\emu-master-dev

echo "Kill adb server"
cmd.exe /c %ANDROID_HOME%\platform-tools\adb.exe kill-server

echo "Cleanup prebuilts"
for /f %%d in ('dir /b C:\buildbot\prebuilt') do (rmdir /s /q C:\buildbot\prebuilt\%%d)

exit 0
