@setlocal enabledelayedexpansion
@echo off

REM This is used to run AVD and console emulator tests.
REM This will be invoked by aosp-emu-master-dev.

set DISTRIB_DIR=%1

setx ANDROID_HOME %SDK_EMULATOR% /M
setx ANDROID_SDK_ROOT %SDK_EMULATOR% /M
setx ANDROID_EMU_ENABLE_CRASH_REPORTING "NO" /M

call refreshenv

set SESSION_DIR=%DISTRIB_DIR%\testlogs
mkdir %SESSION_DIR%

echo "Update emulator, not used, juts for the purpose of sys img dependencies"
echo "Run %ANDROID_HOME%\tools\bin\sdkmanager.bat --channel=3 --install emulator"
cmd.exe /c %ANDROID_HOME%\tools\bin\sdkmanager.bat --channel=3 --install emulator

echo "Deploy emulator"
echo "Run mkdir %SESSION_DIR%\emu-master-dev"
mkdir %SESSION_DIR%\emu-master-dev

set BUILD_DIR=C:\buildbot\prebuilt\%BUILD_NUMBER%\sdk_tools_windows

echo "Run unzip -o %BUILD_DIR%\sdk-repo-windows-emulator-[0-9]*.zip -d %SESSION_DIR%\emu-master-dev\"
unzip -o %BUILD_DIR%\sdk-repo-windows-emulator-[0-9]*.zip -d %SESSION_DIR%\emu-master-dev\

echo "Generate Perf Data"
start cmd /c "title test_timer & python -u external\adt-infra\emu_test\utils\kill_process.py --timeout 7200 --process_regex dotest"
echo "Run python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir Perf_test --file_pattern test_perf.* --config_file external\adt-infra\emu_test\config\perf_cfg_byob.csv --buildername 'Windows_gce' --filter {\"ori\":\"public-perf\"} --timeout 900 --generate_perf"
python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir Perf_test --file_pattern test_perf.* --config_file external\adt-infra\emu_test\config\perf_cfg_byob.csv --buildername Windows_gce --filter {\"ori\":\"public-perf\"} --timeout 900 --generate_perf
for /f %%i in ('python -u kill_process.py --timeout 0 --process_regex kill_process') do set VAR1=%%i
if "%VAR1%" EQU "1" goto PerfTimeOut
goto PerfDone

:PerfTimeOut
echo "Perf test timed out"

:PerfDone
echo "Run python -u external\adt-infra\emu_test\utils\perf_stats.py --log_dir %SESSION_DIR%\Perf_test --api 28"
python -u external\adt-infra\emu_test\utils\perf_stats.py --log_dir %SESSION_DIR%\Perf_test --api 28

echo "Run python -u external\adt-infra\emu_test\utils\perf_stats.py --log_dir %SESSION_DIR%\Perf_test --api 29 --metric_tag 29"
python -u external\adt-infra\emu_test\utils\perf_stats.py --log_dir %SESSION_DIR%\Perf_test --api 29 --metric_tag 29

echo "Zip Perf Data"
7z a %DISTRIB_DIR%\perfgate_data.zip %SESSION_DIR%\Perf_test\test.outputs\*.json

echo "Running Boot tests"
start cmd /c "title test_timer & python -u external\adt-infra\emu_test\utils\kill_process.py --timeout 3600 --process_regex dotest"
echo "Run python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir BOOT_test --file_pattern test_boot.* --config_file external\adt-infra\emu_test\config\boot_cfg_byob.csv --buildername 'Windows_gce' --filter {\"ori\":\"public\"} --timeout 900 --generate_xml"
python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir BOOT_test --file_pattern test_boot.* --config_file external\adt-infra\emu_test\config\boot_cfg_byob.csv --buildername Windows_gce --filter {\"ori\":\"public\"} --timeout 900 --generate_xml
for /f %%i in ('python -u kill_process.py --timeout 0 --process_regex kill_process') do set VAR2=%%i
if "%VAR2%" EQU "1" goto BootTimeOut
goto BootDone

:BootTimeOut
echo "Boot test timed out"

:BootDone
echo "Running AVD tests"
start cmd /c "title test_timer & python -u external\adt-infra\emu_test\utils\kill_process.py --timeout 1200 --process_regex dotest"
echo "Run python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir AVD_test --file_pattern *launch_avd*.* --config_file external\adt-infra\emu_test\config\avd_cfg_byob.csv --buildername 'Windows_gce' --skip-adb-perf --timeout 900 --generate_xml"
python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir AVD_test --file_pattern *launch_avd*.* --config_file external\adt-infra\emu_test\config\avd_cfg_byob.csv --buildername Windows_gce --skip-adb-perf --timeout 900 --generate_xml
for /f %%i in ('python -u kill_process.py --timeout 0 --process_regex kill_process') do set VAR3=%%i
if "%VAR3%" EQU "1" goto AVDTimeOut
goto AVDDone

:AVDTimeOut
echo "AVD test timed out"

:AVDDone
echo "Running Console tests"
start cmd /c "title test_timer & python -u external\adt-infra\emu_test\utils\kill_process.py --timeout 3600 --process_regex dotest"
echo "Run python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir Console_test --file_pattern test_console.* --config_file external\adt-infra\emu_test\config\console_cfg_byob.csv --buildername 'Windows_gce' --skip-adb-perf --timeout 900"
python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir Console_test --file_pattern test_console.* --config_file external\adt-infra\emu_test\config\console_cfg_byob.csv --buildername Windows_gce --skip-adb-perf --timeout 900
for /f %%i in ('python -u kill_process.py --timeout 0 --process_regex kill_process') do set VAR4=%%i
if "%VAR4%" EQU "1" goto ConsoleTimeOut
goto ConsoleDone

:ConsoleTimeOut
echo "Console test timed out"

:ConsoleDone
echo "Running psq snapshot tests"
start cmd /c "title test_timer & python -u external\adt-infra\emu_test\utils\kill_process.py --timeout 1200 --process_regex dotest"
echo "Run python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir Snapshot_test --file_pattern psq_test.* --config_file external\adt-infra\emu_test\config\psq_cfg_byob.csv --buildername 'Windows_gce' --skip-adb-perf --timeout 900 --generate_xml"
python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir Snapshot_test --file_pattern psq_test.* --config_file external\adt-infra\emu_test\config\psq_cfg_byob.csv --buildername Windows_gce --skip-adb-perf --timeout 900 --generate_xml
for /f %%i in ('python -u kill_process.py --timeout 0 --process_regex kill_process') do set VAR5=%%i
if "%VAR5%" EQU "1" goto PsqTimeOut
goto PsqDone

:PsqTimeOut
echo "Psq test timed out"

:PsqDone

mkdir %SESSION_DIR%\cts
pushd %SESSION_DIR%\cts
python setup.py test install --user && python cts\run_basic_cts_tests.py --log %SESSION_DIR%\cts\cts_test.xml -v 1
popd

echo "Remove deployed emulator"
echo "Run rmdir /s /q %SESSION_DIR%\emu-master-dev"
rmdir /s /q %SESSION_DIR%\emu-master-dev

echo "Kill adb server"
cmd.exe /c %ANDROID_HOME%\platform-tools\adb.exe kill-server

echo "Cleanup prebuilts"
for /f %%d in ('dir /b C:\buildbot\prebuilt') do (rmdir /s /q C:\buildbot\prebuilt\%%d)

echo "Cleanup empty files"
for /f %%d in ('dir /s /b /A:-D %SESSION_DIR%') do (if %%~zd==0 del %%d)

exit 0
