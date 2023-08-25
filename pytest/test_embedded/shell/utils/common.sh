# Copyright 2015 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Common routines - do not execute directly.

# So the build bots will only keep build_error.log around in case of failure.
# Because of this it becomes very difficult to track down failures with only partial
# logging turned on.
#
# It also seems that the mixing of stderr & stdout can result in your logs looking out of
# order. Due to this we log to stderr only!

# Sanitize environment
export LANG=C
export LC_ALL=C
TIMEOUT=5400  # overrides the default 2700 seconds timeout. If empty, defaults to 2700.

if [ -z "${SHOW_LOGD}" ]; then
    SHOW_LOGD="true"  # Print additional debug messages.
fi


if [ -z "$_SHU_PROGDIR" ]; then
    _SHU_PROGDIR=$(dirname "$0")
elif [ ! -f "$_SHU_PROGDIR"/common.shi ]; then
    echo "ERROR: Invalid _SHU_PROGDIR value (missing common.shi): $_SHU_PROGDIR"
fi

_SHU_PROGNAME=$(basename "$0")
_SHU_INVOKED="$0 $@"

if [ -t 1 ] ; then
    _RED=`tput setaf 1`
    _GREEN=`tput setaf 2`
    _YELLOW=`tput setaf 3`
    _RESET=`tput sgr0`
else
    _RED=
    _GREEN=
    _YELLOW=
    _RESET=
fi

# Print a debug message to the standard error if $SHOW_LOGD is 'true'
logd() {
    if [ "$SHOW_LOGD" = "true" ]; then
        dump_n -10 "$@" >&2
    fi
}

log2err () {
    log "$@" >&2
}

# Print an error message to stderr then exit the current process.
panic () {
    log2err "${_RED}ERROR: $@${_RESET}"
    exit 1
}

warn () {
    log2err "${_RED}WARNING: $@${_RESET}"
}


# Internal verbosity level. Note that this value is inherited from
# the VERBOSE environment variable.
_SHU_VERBOSE=${VERBOSE:-1}

# Increment internal verbosity level.
increment_verbosity () {
    _SHU_VERBOSE=$(( $_SHU_VERBOSE + 1 ))
}

# Decrement internal verbosity level.
decrement_verbosity () {
    _SHU_VERBOSE=$(( $_SHU_VERBOSE - 1 ))
}

# Set the verbosity to a given level.
set_verbosity () {
    _SHU_VERBOSE=$1
}

# Terminates a process by name
# $1 should be the name of the proc
terminate_proc_by_name() {
    local name=$1
    log "Terminating $name"
    name_procs=$(ps -A | grep "$name" | grep -v grep | awk '{ print $1; }')
    for name_proc in $name_procs; do
        log "Killing: $(ps $name_proc | tail -n 1)"
        silent_run kill -9 $name_proc
    done
}

terminate_adb() {
  terminate_proc_by_name adb
}

# Return internal verbosity level, clamped to 0 as a minimum bound.
get_verbosity () {
    local RET=$_SHU_VERBOSE
    if [ "$RET" -lt 0 ]; then
        RET=0
    fi
    echo "$RET"
}

# Used internally to conditionally print a message.
# $1: message's verbosity level. If greater or equal than $_SHU_VERBOSE then
#     the message will be ignored.
# $2+: message to print to stdout.
dump_n () {
    local LEVEL=$1
    shift
    local cmd="$@"
    if [ "$LEVEL" -lt "$_SHU_VERBOSE" ]; then
        printf '%s %s \n' "$(date '+%H:%M:%S,%3N')" "${cmd}";
    fi
}

# Dump a message to standard error.
# We do this to prevent incorrect interleaving of stderr/stdout.
dump () {
    dump_n 0 "$@" >&2
}

# Dump a message to standard error if --verbose was used.
log () {
    dump_n 1 "$@"
}

# Dump a message to standard error if --verbose --verbose is used.
log2 () {
    dump_n 2 "$@"
}

# Run a command, but suppress stdout
# keep stderr open in case error
silent_run () {
    "$@" >/dev/null
}

# Run a command, output depends on verbosity level
run () {
    local VERBOSE=$_SHU_VERBOSE
    if [ "$VERBOSE" -lt 0 ]; then
        VERBOSE=0
    fi
    if [ "$VERBOSE" -gt 1 ]; then
        log "${_GREEN}COMMAND: $@${_RESET}"
    fi
    case $VERBOSE in
        0|1)
             "$@" >/dev/null 2>&1
             ;;
        2)
            "$@" >/dev/null
            ;;
        *)
            "$@" >&2
            ;;
    esac
}

# Return the current script's directory.
program_directory () {
    printf "%s" "$_SHU_PROGDIR"
}

# Return the current script's filename.
program_name () {
    printf "%s" "$_SHU_PROGNAME"
}

# Return the value of a given named variable.
# $1: variable name
#
# example:
#    FOO=BAR
#    BAR=ZOO
#    echo `var_value $FOO`
#    will print 'ZOO'
#
var_value () {
    eval printf %s \"\$$1\"
}

# Return success if variable $1 is set and non-empty, failure otherwise.
# $1: Variable name.
# Usage example:
#   if var_is_set FOO; then
#      .. Do something the handle FOO condition.
#   fi
var_is_set () {
    test -n "$(var_value $1)"
}

_var_quote_value () {
    printf %s "$1" | sed -e "s|'|\\'\"'\"\\'|g"
}

# Set the value of a given name variables.
# $1: Variable name.
# $2+: Variable value.
# example:
#    FOO=BAR
#    var_assign $FOO bar
# is equivalent to
#    BAR=bar
var_assign () {
    local _var_assign_varname _var_assign_value
    _var_assign_varname=$1
    shift
    _var_assign_value=$(_var_quote_value "$*")
    eval $_var_assign_varname=\'$_var_assign_value\'
}

# Append a space-separated list of items to a given variable.
# $1: Variable name.
# $2+: Variable value.
# Example:
#   FOO=
#   var_append FOO foo    (FOO is now 'foo')
#   var_append FOO bar    (FOO is now 'foo bar')
#   var_append FOO zoo    (FOO is now 'foo bar zoo')
var_append () {
    local _var_append_varname
    _var_append_varname=$1
    shift
    if test "$(var_value $_var_append_varname)"; then
        eval $_var_append_varname=\$$_var_append_varname\'\ $(_var_quote_value "$*")\'
    else
        eval $_var_append_varname=\'$(_var_quote_value "$*")\'
    fi
}

# Import shell script $1. Similar to sourcing the script except
# that each script will only be sourced once, even with multiple
# dependencies.
shell_import () {
    local SCRIPT="$_SHU_PROGDIR/$1"
    if [ ! -f "$SCRIPT" ]; then
        panic "Missing script: $SCRIPT"
    fi
    local SCRIPT_TAG=_SHU_SHELL_SCRIPT_TAG__${1%%.shi}
    SCRIPT_TAG=$(echo "$SCRIPT_TAG" | tr '-' '_' | tr '/' '__')
	case $(var_value $SCRIPT_TAG) in
        imported)
            # Script is already imported.
            return 0
            ;;
        importing)
            # Script is already being imported, this is
            # a circular dependency.
            panic "Circular dependency when trying to import $1"
            ;;
        *)
            # Import the script.
            var_assign $SCRIPT_TAG importing
            . "$SCRIPT"
            var_assign $SCRIPT_TAG imported
            ;;
    esac
}

# Return the build machine's operating system tag.
# Valid return values are:
#    linux
#    darwin
#    freebsd
#    windows   (really MSys)
#    cygwin
get_build_os () {
    if [ -z "$_SHU_BUILD_OS" ]; then
        _SHU_BUILD_OS=$(uname -s)
        case $_SHU_BUILD_OS in
            Darwin)
                _SHU_BUILD_OS=darwin
                ;;
            FreeBSD)  # note: this is not tested
                _SHU_BUILD_OS=freebsd
                ;;
            Linux)
                # note that building  32-bit binaries on x86_64 is handled later
                _SHU_BUILD_OS=linux
                ;;
            CYGWIN*|*_NT-*)
                _SHU_BUILD_OS=windows
                if [ "x$OSTYPE" = xcygwin ] ; then
                    _SHU_BUILD_OS=cygwin
                fi
                ;;
        esac
    fi
    echo "$_SHU_BUILD_OS"
}

# Return the build machine's CPU architecture.
# Valid return values are:
#     x86
#     x86_64
#     aarch64
get_build_arch () {
    local TEST
    if [ -z "$_SHU_BUILD_ARCH" ]; then
        case $(get_build_os) in
            linux|darwin)
                _SHU_BUILD_ARCH=$(uname -m)
                # Kernel bitness might not match user space, so test
                # the bitness of our shell to know what the user is
                # really running.
                TEST=$(/usr/bin/file -L $SHELL 2>/dev/null | grep 'x86[_-]64' || true)
                if [ "$TEST" ]; then
                    _SHU_BUILD_ARCH=x86_64
                fi
                ;;
            windows|cygwin)
                case $PROCESSOR_ARCHITECTURE in
                    ADM64)
                        _SHU_BUILD_ARCH=x86_64
                        ;;
                    *)
                        _SHU_BUILD_ARCH=x86
                        ;;
                esac
                ;;
            *)
                _SHU_BUILD_ARCH=$(uname -p)
                ;;
        esac
    fi
    echo "$_SHU_BUILD_ARCH"
}

# Return the executable extension for a given operating system tag.
# $1: operating system tag.
_shu_get_exe_extension_for () {
    case $1 in
        windows|cygwin)
            echo ".exe"
            ;;
        *)
            echo ""
    esac
}

# Return the dynamic library extension for a given operating system tag.
# $1: operating system tag.
_shu_get_dll_extension_for () {
    case $1 in
        darwin)
            echo ".dylib"
            ;;
        windows|cygwin)
            echo ".dll"
            ;;
        *)
            echo ".so"
            ;;
    esac
}

# Return the number of CPU cores on the build machine.
get_build_num_cores () {
    case $(get_build_os) in
        linux)
            grep -c -e processor /proc/cpuinfo 2>/dev/null || echo 1
            ;;
        darwin|freebsd)
            sysctl -n hw.ncpu 2>/dev/null || echo 1
            ;;
        windows|cygwin)
            echo "${NUMBER_OF_PROCESSORS:-1}"
            ;;
        *)
            echo "1"
            ;;
    esac
}

# Convert commas into spaces.
# $1: input string
# Out: input string, with each comma replaced by a space.
commas_to_spaces () {
    printf "%s" "$@" | tr ',' ' '
}

# Convert spaces into commas
# $1+: input string
# Out: input string, with contiguous spaces replaced by a comma.
# NOTE: This also strips leading/trailing space.
spaces_to_commas () {
    local ITEM RET
    for ITEM in $*; do
        if [ -z "$RET" ]; then
            RET=$ITEM
        else
            RET="$RET,$ITEM"
        fi
    done
    printf "%s" "$RET"
}

# Return success iff item |$2| is in list |$1|.
# $1: input list
# $2: item to find in list.
list_contains () {
    local ITEM
    for ITEM in $(commas_to_spaces "$1"); do
        if [ "$ITEM" = "$2" ]; then
            return 0
        fi
    done
    return 1
}

# Copy a directory, create target location if needed
#
# $1: source directory
# $2: target directory location
#
copy_directory ()
{
    local SRCDIR="$1"
    local DSTDIR="$2"
    if [ ! -d "$SRCDIR" ] ; then
        panic "Can't copy from non-directory: $SRCDIR"
    fi
    log "Copying directory: from [$SRCDIR] to [$DSTDIR]"
    mkdir -p "$DSTDIR" && (cd "$SRCDIR" && 2>/dev/null tar cf - *) | (tar xf - -C "$DSTDIR") ||
            panic "Cannot copy to directory: $DSTDIR"
}

# $1: source directory
# $2: target directory location
# $3+: list of file names and filters.
copy_directory_files ()
{
    local SRCDIR="$1"
    local DSTDIR="$2"
    shift
    shift
    if [ ! -d "$SRCDIR" ] ; then
        panic "Can't copy from non-directory: $SRCDIR"
    fi
    log "Copying directory: from [$SRCDIR] to [$DSTDIR]"
    mkdir -p "$DSTDIR" || panic "Cannot create target directory: $DSTDIR"
    (cd "$SRCDIR" && 2>/dev/null tar cf - "$@" | \
            tar xf - -C "$DSTDIR") ||
        panic "Cannot copy to directory: $DSTDIR"
}

# Creates the given directory if it doesn't exist yet
# $1: Directory to create
make_if_not_exists()
{
    local DESTDIR="$1"
    if [ ! -d $DESTDIR ]; then
       run mkdir -p ${DESTDIR} || panic "Unable to create ${DESTDIR}"
    else
       log2 "Directory: ${DESTDIR} already exists"
    fi
}

# Compute the SHA-1 sum of a given file. Implementation depends on the
# current host machine.
# $1: File path
# Out: SHA-1 sum as an hexadecimal string.
compute_file_sha1 () {
    case $(get_build_os) in
        linux)
            (sha1sum "$1" | awk '{ print $1; }') 2>/dev/null
            ;;
        darwin)
            (openssl sha1 "$1" | awk '{ print $2; }') 2>/dev/null
            ;;
        *)
            panic "Don't know how to compute a SHA-1 sum on this platform: \
$(get_build_os)"
    esac
}

# Return the file path of a given timestamp
# $1: Installation directory
# $2: Timestamp group name
_shu_timestamp_file () {
    printf %s "$1/timestamps/$2"
}

timestamp_check () {
    test -f "$(_shu_timestamp_file "$1" "$2")"
}

timestamp_set () {
    local TIMESTAMP="$(_shu_timestamp_file "$1" "$2")"
    run mkdir -p "$(dirname $TIMESTAMP)" && run touch "$TIMESTAMP"
}

timestamp_clear () {
    run rm -f "$(_shu_timestamp_file "$1" "$2")"
}

# Find a given program in the current path. This function never fails.
# $1: Program name
# Out: program path, if found, or empty string otherwise.
find_program () {
    which "$1" 2>/dev/null || true
}



log_invocation() {
    # Log the invocation of this command, this makes
    # reading the build logs a lot easier.
    dump "Running: $_SHU_INVOKED"
}

run_timeout() {
    # Runs the given command with the given timeout, logging all output to
    # stderr.
    #
    # Within the given timeout, checks for the existence of the process at
    # regular intervals.
    #
    # $1 Timeout in seconds after which a kill -9 signal will be sent.
    # $@ Command to be executed.

    local timeout
    if [ -n "${TIMEOUT}" ]; then
        timeout="${TIMEOUT}"
    else
        timeout=$1
    fi

    shift
    declare -i interval=1  # Interval between checks if the process is still alive.
    declare -i delay=1  # Delay between the posting of the signals SIGTERM and SIGKILL.

    log2err "${_GREEN}COMMAND: ${timeout} seconds for  $@${_RESET}"
    logd "${_GREEN}run_timeout: ${timeout} seconds for executing '"$@"${_RESET}'"
    logd "run_timeout: called run_timeout from parent PID $PPID"

        (
            pid=$(exec sh -c 'echo $PPID')  # PID of the subshell
            logd "run_timeout: entered subshell (PID $pid) on which the command will run."

            (
                pid_subsubshell="$(exec sh -c 'echo $PPID')"
                logd "run_timeout: entered detached subshell (PID "${pid_subsubshell}") for the sleep function."
                ((t = timeout))

                # Wait timeout (t) seconds before posting the SIGTERM and SIGKILL signals.
                logd "run_timeout: waiting the ${timeout}s timeout has started ..."
                while ((t > 1)); do
                    sleep $interval
                    # Check every $interval seconds for the existence of the process with PID $pid.
                    # If $pid doesn't exist, (e.g. process terminated), 'exit 0' quits the subshell.
                    kill -0 $pid > /dev/null 2>&1
                    if [ $? -eq 1 ]; then
                        logd "run_timeout: killing PID $pid no more possible. Exiting subshell "${pid_subsubshell}"."
                        exit 0
                    fi
                    ((t -= interval))
                done

                # SIGTERM (15) is called first. Then SIGKILL (9).
                # `kill -0 $pid` checks if it is possible to kill the process.
                # `exit 0` will be executed if any of the previous commands fail.
                logd "run_timeout: reached timeout of ${timeout}s. Killing process $pid."
                logd "run_timeout: sending SIGTERM to process $pid"

                kill -15 $pid > /dev/null 2>&1
                kill -0 $pid > /dev/null 2>&1

                if [ $? -eq 1 ]; then
                    exit 0  # Exiting subshell
                fi
                sleep $delay

                logd "run_timeout: sending SIGKILL to process $pid"
                kill -9 $pid > /dev/null 2>&1
            ) &

            eval "$@"
        )

        # kill -9 (SIGKILL) results in 137 (128+9).
        # kill -15 (SIGTERM) results in 143 (128+15).
        if [[ $? -eq 137 || $? -eq 143 ]]; then
            STATUS=1
            warn "Command timed out after $timeout seconds!"
            logd "run_timeout: command "$@" timed out after $timeout seconds!"
        fi

        while { kill -0 $pid > /dev/null 2>&1; } do
            sleep 1;
        done
        logd "run_timeout: command terminated successfully!"

        # Double check if there is a sleep process with timeout $timeout_seconds.
        local pid_sleep="$(pgrep sleep -a | grep -w "sleep "$timeout"" | cut -d' ' -f1)"
        if [ -z "${pid_sleep}" ]; then
            logd "run_timeout: no sleep processes with timeout ${timeout}s detected."
        else
            logd "run_timeout: there is still a sleep process alive (PID "${pid_sleep}")"
        fi
        
}

run_test() {
    # Runs the given test with a timeout of at most 15 minutes.
    # If a timeout is reached it will set the STATUS variable
    # to 1.
    # All the output of the test command will be redirected to stderr
    # $1 = The name of the test, displayed in the log
    # $@ = The command of the test to be run.
    local test_name=$1
    shift
    local test_cmd=$@

    # The build bots will only share stderr in case of presubmit failures,
    # So we are going to redirect all stdout -> stderr to make sure we can
    # see failures on the build_err log
    log2err "Running ${test_name}"

    # Tests can take a while to run on a mac.
    run_timeout 2700 ${test_cmd}
}

clean_avds() {
    log "Remove any existing AVDs"
    run rm -rf $ANDROID_AVD_HOME/*
}

check_vars()  {
    for ITEM in $@; do
        log "Using $ITEM = $(var_value $ITEM)"
        var_is_set $ITEM || panic "[$ITEM] is not set!"
    done
}

check_test_succeed() {
    # Checks if the given test has a junit test report and has no failures/errors in the test report
    local TEST_DIR=$1
    local TEST_REPORT=$SESSION_DIR/$TEST_DIR/test_${TEST_DIR}.xml
    [[ ! -f $TEST_REPORT ]] && panic "Test report $TEST_REPORT not found"

    # We specifically check if there are failure or error elements in the xml.
    # See https://github.com/windyroad/JUnit-Schema/blob/master/JUnit.xsd for the xsd

    # An <error> element indicates that the test errored. An errored test is one that had an
    # unanticipated problem. e.g., an unchecked throwable; or a problem with the
    # implementation of the test.
    xmllint --xpath "//error" $TEST_REPORT && panic "Errors in $TEST_DIR"

    # A <failure> element indicates the test failed.
    # A failure is a test which the code has explicitly failed by using the mechanisms
    # for that purpose. e.g., via an assertEquals.
    xmllint --xpath "//failure" $TEST_REPORT && panic "Failures in $TEST_DIR"
}

# Setup virtualenv if available
activate_virtualenv() {
  local UTIL_DIR=$1
  mkdir py3env
  pushd py3env
  python3 -m venv env
  popd
  source py3env/env/bin/activate
  pip3 install -r $UTIL_DIR/requirements.txt
}

deactivate_virtualenv() {
  deactivate
  rm -rf py3env
}

# Returns true if the string starts with a P or p
is_presubmit () {
  retval=false
  case $1 in
    P* ) retval=true;;
    p* ) retval=true;;
  esac
  printf "$retval"
}

check_physical_display() {
    case $(get_build_os) in
        darwin)
            output=$(system_profiler SPDisplaysDataType)
            printf ">> system_profiler SPDisplaysDataType\n$output\n"
            # Example output:
            # Graphics/Displays:
            #
            #     Apple M1 Pro:
            #
            #       Chipset Model: Apple M1 Pro
            #       Type: GPU
            #       Bus: Built-In
            #       Total Number of Cores: 16
            #       Vendor: Apple (0x106b)
            #       Metal Support: Metal 3
            #       Displays:  ### This will be absent if no display is detected
            #         Color LCD:
            #           Display Type: Built-in Liquid Retina XDR Display
            #           Resolution: 3456 x 2234 Retina
            #           Main Display: Yes
            #           Mirror: Off
            #           Online: Yes
            #           Automatically Adjust Brightness: Yes
            #           Connection Type: Internal
            display_type=$(system_profiler SPDisplaysDataType | grep "^[[:blank:]]*Displays:")
            if [ -z "$display_type" ]; then
                panic "No physical display detected. Skipping tests and marking build as failed."
            else
                printf "Display type found.\n"
            fi
            ;;
        *)
            ;;
    esac
}

PYTHON="python3"

# Check that python is installed and working.
PYVER=$($PYTHON --version)
log "Using python version: $PYVER"
