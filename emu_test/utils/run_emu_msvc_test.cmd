@setlocal enabledelayedexpansion
@echo off

REM This is used to run emulator test for msvc build.
REM This will be invoked by aosp-emu-master-dev.

set DISTRIB_DIR=%1

setx ANDROID_HOME %SDK_EMULATOR% /M
setx ANDROID_SDK_ROOT %SDK_EMULATOR% /M
setx ANDROID_EMU_ENABLE_CRASH_REPORTING "NO" /M

call refreshenv

set SESSION_DIR=%DISTRIB_DIR%\testlogs
mkdir %SESSION_DIR%

echo "Deploy emulator"
echo "Run mkdir %SESSION_DIR%\emu-master-dev"
mkdir %SESSION_DIR%\emu-master-dev

set BUILD_DIR=C:\buildbot\prebuilt\%BUILD_NUMBER%\sdk_tools_windows

echo "Run unzip -o %BUILD_DIR%\sdk-repo-windows-emulator-[0-9]*.zip -d %SESSION_DIR%\emu-master-dev\"
unzip -o %BUILD_DIR%\sdk-repo-windows-emulator-[0-9]*.zip -d %SESSION_DIR%\emu-master-dev\

if "%BUILD_NUMBER:~0,1%"=="P" goto RunBootTests

echo "Generate Perf Data"
start cmd /c "title test_timer & python -u external\adt-infra\emu_test\utils\test_timer.py --timeout 5400"
echo "Run python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir Perf_test --file_pattern test_perf.* --config_file external\adt-infra\emu_test\config\perf_cfg_byob.csv --buildername 'Windows_gce' --filter {\"ori\":\"public-perf\"} --timeout 900 --generate_perf"
python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir Perf_test --file_pattern test_perf.* --config_file external\adt-infra\emu_test\config\perf_cfg_byob.csv --buildername Windows_gce --filter {\"ori\":\"public-perf\"} --timeout 900 --generate_perf
tasklist /v | find "test_timer"
if errorlevel 1 goto PerfTimeOut
taskkill /fi "windowtitle eq Administrator:  test_timer*"
goto PerfDone

:PerfTimeOut
echo "Perf test timed out"

:PerfDone
echo "Run python -u external\adt-infra\emu_test\utils\perf_stats.py --log_dir %SESSION_DIR%\Perf_test --metric_tag msvc --api 28"
python -u external\adt-infra\emu_test\utils\perf_stats.py --log_dir %SESSION_DIR%\Perf_test --metric_tag msvc --api 28

echo "Run python -u external\adt-infra\emu_test\utils\perf_stats.py --log_dir %SESSION_DIR%\Perf_test --metric_tag msvc_29 --api 29"
python -u external\adt-infra\emu_test\utils\perf_stats.py --log_dir %SESSION_DIR%\Perf_test --metric_tag msvc_29 --api 29

echo "Zip Perf Data"
7z a %DISTRIB_DIR%\perfgate_data.zip %SESSION_DIR%\Perf_test\test.outputs\*.json

:RunBootTests

echo "Running Boot tests"
start cmd /c "title test_timer & python -u external\adt-infra\emu_test\utils\test_timer.py --timeout 3600"
echo "Run python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir BOOT_test --file_pattern test_boot.* --config_file external\adt-infra\emu_test\config\boot_cfg_byob.csv --buildername 'Windows_gce' --filter {\"ori\":\"public\"} --timeout 900 --generate_xml"
python -u external\adt-infra\emu_test\dotest.py --loglevel DEBUG --session_dir %SESSION_DIR% --emulator %SESSION_DIR%\emu-master-dev\emulator\emulator --test_dir BOOT_test --file_pattern test_boot.* --config_file external\adt-infra\emu_test\config\boot_cfg_byob.csv --buildername Windows_gce --filter {\"ori\":\"public\"} --timeout 900 --generate_xml
tasklist /v | find "test_timer"
if errorlevel 1 goto BootTimeOut
taskkill /fi "windowtitle eq Administrator:  test_timer*"
goto BootDone

:BootTimeOut
echo "Boot test timed out"

:BootDone

mkdir %SESSION_DIR%\cts
pushd cts
python setup.py test install --user && python cts\run_basic_cts_tests.py --log %SESSION_DIR%\cts\cts_test.xml -v 1
popd


echo "Remove deployed emulator"
echo "Run rmdir /s /q %SESSION_DIR%\emu-master-dev"
rmdir /s /q %SESSION_DIR%\emu-master-dev

echo "Cleanup prebuilts"
for /f %%d in ('dir /b C:\buildbot\prebuilt') do (rmdir /s /q C:\buildbot\prebuilt\%%d)

echo "Cleanup empty files"
for /f %%d in ('dir /s /b /A:-D %SESSION_DIR%') do (if %%~zd==0 del %%d)

exit 0
