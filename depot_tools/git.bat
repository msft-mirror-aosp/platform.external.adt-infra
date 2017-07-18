@echo off
setlocal
if not defined EDITOR set EDITOR=notepad
set PATH=%~dp0git-2.10.0-64_bin\cmd;%~dp0;%PATH%
"%~dp0git-2.10.0-64_bin\cmd\git.exe" %*
