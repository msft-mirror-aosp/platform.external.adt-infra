@echo off
REM Runs FoldableDisplayTest locally on Windows against an already-running foldable emulator.
REM Extra arguments are passed on to Tradefed, e.g. -s emulator-5554 to pick the device.
REM The Tradefed logs and results (foldable_display_video .mp4, screenshots, and ffmpeg logs)
REM are copied to %ETS_FOLDABLE_OUT_DIR%, by default out\ets_foldable\<timestamp> under the repo
REM root, and reported to Sponge like run_external.sh's.
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..\..\..") do set "REPO_ROOT=%%~fI"

set "BAZEL=%REPO_ROOT%\prebuilts\bazel\windows-x86_64\bazel.exe"

set "ETS_BAZEL_FLAGS="
set "ETS_BUSYBOX_SH="
if defined BAZEL_SH if /i not "!BAZEL_SH:busybox=!"=="!BAZEL_SH!" set "ETS_BUSYBOX_SH=1"
if defined ETS_BUSYBOX_SH (
  for %%B in ("%ProgramFiles%\Git\usr\bin\bash.exe" "%ProgramFiles%\Git\bin\bash.exe" "%LOCALAPPDATA%\Programs\Git\usr\bin\bash.exe" "C:\msys64\usr\bin\bash.exe") do (
    if not defined ETS_BASH if exist "%%~B" set "ETS_BASH=%%~B"
  )
  if defined ETS_BASH (
    echo BAZEL_SH is busybox, which cannot run the unzip script and commands rules_android uses. Building the ETS with !ETS_BASH! instead.
    set "ETS_BAZEL_FLAGS="--shell_executable=!ETS_BASH!" "--repo_env=BAZEL_SH=!ETS_BASH!" "--experimental_override_name_platform_in_output_dir=@goldfish_build//platforms:windows_x64=ets""
  ) else (
    echo WARNING: BAZEL_SH is busybox and no Git Bash or MSYS2 bash was found. The ETS build may fail with "unzip: Exec format error".
  )
)

pushd "%REPO_ROOT%"
"%BAZEL%" build %ETS_BAZEL_FLAGS% @goldfish_test//ets:android_ets_zip
if errorlevel 1 (
  popd
  exit /b 1
)
for /f "delims=" %%I in ('call "%BAZEL%" info execution_root 2^>nul') do set "EXEC_ROOT=%%I"
for /f "delims=" %%F in ('call "%BAZEL%" cquery %ETS_BAZEL_FLAGS% --output=files @goldfish_test//ets:android_ets_zip 2^>nul') do set "ETS_ZIP=%EXEC_ROOT%/%%F"
if not defined ETS_ZIP (
  echo Could not locate the output of @goldfish_test//ets:android_ets_zip with bazel cquery.
  popd
  exit /b 1
)
set "ETS_ZIP=%ETS_ZIP:/=\%"

if defined ETS_WORK_DIR (set "WORK_DIR=%ETS_WORK_DIR%") else set "WORK_DIR=%TEMP%\ets_foldable_%RANDOM%"
if not exist "%WORK_DIR%\ets" mkdir "%WORK_DIR%\ets"

echo Extracting %ETS_ZIP% into %WORK_DIR%
powershell -NoProfile -Command "Expand-Archive -Path '%ETS_ZIP%' -DestinationPath '%WORK_DIR%\ets' -Force"

set "DISPLAY_DIR=%REPO_ROOT%\tools\emulator\testlib\display"
set "DISPLAY_DIR=!DISPLAY_DIR:\=/!"
set "DISPLAY_DIR=!DISPLAY_DIR::=\:!"

call "%WORK_DIR%\ets\android-ets\tools\ets-tradefed.bat" run commandAndExit ets ^
  -m FoldableDisplayTest ^
  --module-arg "FoldableDisplayTest:set-option:display_dir:!DISPLAY_DIR!" ^
  %*

popd

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%..\ui\check_tradefed_results.ps1" "%WORK_DIR%\ets\android-ets\results" 1
set "EXIT_CODE=%ERRORLEVEL%"

if not defined ETS_FOLDABLE_OUT_DIR for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "ETS_FOLDABLE_OUT_DIR=%REPO_ROOT%\out\ets_foldable\%%T"
if exist "%WORK_DIR%\ets\android-ets\logs" robocopy "%WORK_DIR%\ets\android-ets\logs" "%ETS_FOLDABLE_OUT_DIR%\logs" /E >nul
if exist "%WORK_DIR%\ets\android-ets\results" robocopy "%WORK_DIR%\ets\android-ets\results" "%ETS_FOLDABLE_OUT_DIR%\results" /E >nul
echo Test outputs (videos, screenshots, logs): %ETS_FOLDABLE_OUT_DIR%

if not defined ETS_WORK_DIR rmdir /s /q "%WORK_DIR%"
if not defined ETS_WORK_DIR call "%SCRIPT_DIR%..\ui\report_to_sponge.bat" "%ETS_FOLDABLE_OUT_DIR%" 1
exit /b %EXIT_CODE%
