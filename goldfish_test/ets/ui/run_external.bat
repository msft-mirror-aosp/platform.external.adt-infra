@echo off
REM Runs DeviceHubUiTest locally on Windows against an already-running emulator.
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..\..\..") do set "REPO_ROOT=%%~fI"

set "BAZEL=%REPO_ROOT%\prebuilts\bazel\windows-x86_64\bazel.exe"
set "HUB_ZIP=%REPO_ROOT%\prebuilts\android-emulator-build\common\android-device-hub\win32-x64\device-hub_pack_win32_x64.zip"

pushd "%REPO_ROOT%"
"%BAZEL%" build @goldfish_test//ets:android_ets_zip
if errorlevel 1 (
  popd
  exit /b 1
)

set "WORK_DIR=%TEMP%\ets_ui_%RANDOM%"
mkdir "%WORK_DIR%\ets"
mkdir "%WORK_DIR%\hub"

powershell -NoProfile -Command "Expand-Archive -Path '%REPO_ROOT%\bazel-bin\external\goldfish_test+\ets\android-ets.zip' -DestinationPath '%WORK_DIR%\ets' -Force"
powershell -NoProfile -Command "Expand-Archive -Path '%HUB_ZIP%' -DestinationPath '%WORK_DIR%\hub' -Force"

REM Tradefed's set-option splits on ":", so "C:\..." would be read as option "C".
REM Pass the paths with forward slashes and an escaped drive-letter colon instead.
set "HUB_EXE=%WORK_DIR%\hub\android_device_hub.exe"
set "DISPLAY_DIR=%REPO_ROOT%\tools\emulator\testlib\display"
call :tradefed_path HUB_EXE
call :tradefed_path DISPLAY_DIR

call "%WORK_DIR%\ets\android-ets\tools\ets-tradefed.bat" run commandAndExit ets ^
  -m DeviceHubUiTest ^
  --module-arg "DeviceHubUiTest:set-option:device_hub_path:!HUB_EXE!" ^
  --module-arg "DeviceHubUiTest:set-option:display_dir:!DISPLAY_DIR!" ^
  %*
set "EXIT_CODE=%ERRORLEVEL%"

rmdir /s /q "%WORK_DIR%"
popd
exit /b %EXIT_CODE%

REM Rewrites the path in variable %1 to C\:/dir/file form for tradefed set-option.
:tradefed_path
set "_path=!%1!"
set "_path=!_path:\=/!"
set "_path=!_path::=\:!"
set "%1=!_path!"
exit /b 0
