@echo on
@REM  Copyright 2023 The Android Open Source Project
@REM
@REM  Licensed under the Apache License, Version 2.0 (the "License");
@REM  you may not use this file except in compliance with the License.
@REM  You may obtain a copy of the License at
@REM
@REM       http:\\www.apache.org\licenses\LICENSE-2.0
@REM
@REM  Unless required by applicable law or agreed to in writing, software
@REM  distributed under the License is distributed on an "AS IS" BASIS,
@REM  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
@REM  See the License for the specific language governing permissions and
@REM  limitations under the License.

@REM  Point ANDROID_SDK_ROOT to the one that we ship
set AOSP_ROOT=%~dp0\..\..\..\..
set REPO_DIR=%AOSP_ROOT%\external\adt_infra\devpi\repo
set SDK_EMULATOR=%AOSP_ROOT%\prebuilts\android-emulator-build\system-images\windows
set ANDROID_HOME=%SDK_EMULATOR%
set ANDROID_SDK_ROOT=%SDK_EMULATOR%
set AEMU_GRPC=%AOSP_ROOT%\external\qemu\android\android-grpc\python\aemu-grpc\
set SNAPTOOL=%AOSP_ROOT%\external\qemu\android\android-grpc\python\snaptool\
set NETSIM_GRPC=%AOSP_ROOT%\tools\netsim\testing\netsim-grpc\

if exist .venv\Scripts\activate (
    rem Ignore
) else (
    PYTHON -m venv .venv
)
call .venv\Scripts\activate

pip install --upgrade pip wheel setuptools
pip install wheel %AEMU_GRPC% %SNAPTOOL% %NETSIM_GRPC%
