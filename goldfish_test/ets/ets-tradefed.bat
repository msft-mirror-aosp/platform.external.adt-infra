@echo off
REM Run from the parent directory of this file.
cd %~dp0
cd ..
java -XX:+HeapDumpOnOutOfMemoryError -XX:-OmitStackTraceInFastThrow -cp tools\e2e_tests_pre_deploy.jar;tools\compatibility-host-util.jar;tools\compatibility-tradefed.jar;tools\loganalysis.jar;tools\tradefed-avd-util-tests.jar;tools\tradefed-contrib.jar;tools\tradefed-isolation-tests.jar;tools\tradefed.jar;tools\tradefed-tests.jar;tools\e2e_tests_post_deploy.jar com.android.tradefed.command.Console %*

