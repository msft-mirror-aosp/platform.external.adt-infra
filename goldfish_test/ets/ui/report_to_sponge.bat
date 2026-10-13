@echo off
REM Reports a run of run_local.bat or run_external.bat to Sponge the way Bazel reports run_local.sh
REM and run_external.sh: runs @goldfish_test//ets/ui:report_results (see report_results.py) on the
REM output directory of the run with --config=rcache, which makes Bazel upload the test log, the
REM JUnit XML and the outputs, and --config=sponge, which streams the invocation, and prints the
REM Fusion link. Exits with bazel's exit code: 3 when the reported run failed, 0 when it passed.
REM   report_to_sponge.bat <out\ets_ui\timestamp directory> <number of Tradefed invocations expected>
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..\..\..") do set "REPO_ROOT=%%~fI"
set "BAZEL=%REPO_ROOT%\prebuilts\bazel\windows-x86_64\bazel.exe"

REM Pick the invocation id here so that the Fusion link can be printed even if bazel fails.
for /f %%I in ('powershell -NoProfile -Command "[guid]::NewGuid().ToString()"') do set "INVOCATION_ID=%%I"
pushd "%REPO_ROOT%"
"%BAZEL%" test --config=rcache --config=sponge --invocation_id=%INVOCATION_ID% --nocache_test_results --zip_undeclared_test_outputs --test_output=errors "--test_arg=--out_dir=%~1" --test_arg=--min_results=%~2 @goldfish_test//ets/ui:report_results
set "EXIT_CODE=!ERRORLEVEL!"
popd
if not "!EXIT_CODE!"=="0" if not "!EXIT_CODE!"=="3" echo Could not report the results to Sponge, bazel exited with !EXIT_CODE!.
echo Sponge: https://fusion2.corp.google.com/invocations/%INVOCATION_ID%
exit /b %EXIT_CODE%
