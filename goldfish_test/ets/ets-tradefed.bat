@echo off
REM Run from the parent directory of this file.
cd %~dp0
cd ..
REM Like ets-tradefed's TF_PATH_PREPEND: the protobuf jars go first so that the gRPC gencode in the
REM e2e tests gets the protobuf runtime it was built with rather than the older one in tradefed.jar.
java -XX:+HeapDumpOnOutOfMemoryError -XX:-OmitStackTraceInFastThrow -cp tools\protobuf_java.jar;tools\protobuf_javalite.jar;tools\protobuf_javalite_runtime.jar;tools\e2e_tests_pre_deploy.jar;tools\compatibility-host-util.jar;tools\compatibility-tradefed.jar;tools\loganalysis.jar;tools\tradefed-avd-util-tests.jar;tools\tradefed-contrib.jar;tools\tradefed-isolation-tests.jar;tools\tradefed.jar;tools\tradefed-tests.jar;tools\e2e_tests_post_deploy.jar com.android.tradefed.command.Console %*

