@echo off
REM Run from the parent directory of this file.
cd %~dp0
cd ..
java -XX:+HeapDumpOnOutOfMemoryError -XX:-OmitStackTraceInFastThrow -cp tools\* com.android.tradefed.command.Console %*
