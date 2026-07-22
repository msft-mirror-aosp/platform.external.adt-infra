# Copyright 2022 - The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the',  help='License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an',  help='AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
import logging
import platform
import sys

import psutil


def safe_kill(process: psutil.Process) -> bool:
    """Tries to kill the given process

    Args:
        process (psutil.Process): The process to be terminated

    Returns:
        bool: True if the process is no longer alive.
    """
    status = psutil.STATUS_DEAD
    try:
        status = process.status()
        process.name()  # Retrieve name if possible.
    except Exception as e:
        # Process has left, or we might have been unable to get additional info.
        logging.debug("Unable to get status, process dead? %s", e)

    if status == psutil.STATUS_ZOMBIE:
        # confirm that the zombie process has been reaped
        try:
            # the process is a zombie, so we need to wait for the parent to reap it
            parent_pid = process.ppid()
            parent = psutil.Process(parent_pid)

            # wait for the parent to reap the zombie process
            parent.wait(timeout=1)
        except Exception as err:
            # well, well, well.. Someone just disappeared on us..
            # or we failed to wait out the reaping. It will get
            # cleaned up later on
            logging.info("Failed to reap zombie, ignoring %s", err)

        if not psutil.pid_exists(process.pid):
            logging.info("Process %s has been reaped.", process)

    # Step 1, be nice.
    try:
        logging.debug("Terminate %s", process)
        process.terminate()
    except Exception as e:
        # Process might be gone, or we could not send terminate.
        logging.debug("Failed to terminate %s due to %s", process, e)

    try:
        process.wait(timeout=3)
    except psutil.TimeoutExpired:
        logging.debug("Force kill %s", process)
        process.kill()

    if not psutil.pid_exists(process.pid):
        logging.info("Successfully terminated: %s", process)

    return not psutil.pid_exists(process.pid)


def kill_process_tree(process: psutil.Process) -> None:
    """
    Kills the process tree rooted at the given process.

    Args:
        process: The root process of the process tree to kill.
    """
    children = process.children()
    for child in children:
        logging.debug("Found child %s, terminating..", child)
        kill_process_tree(child)

    safe_kill(process)


def is_emulator_process(
    process: psutil.Process,
    emulator_process_names="emulator,qemu-system,netsim,netsimd,netsimdx",
) -> bool:
    """Checks if the given process is an emulator (or related) process

    This includes: emulator, qemu-system.*, netsim, netsimd

    Args:
        process (psutil.Process): The process to check

    Returns:
        bool: True if this is an emulator related process
    """
    emulator_process_names = [x.strip() for x in emulator_process_names.split(",")]
    try:
        name = process.name()
        logging.debug("Checking %s in %s", name, emulator_process_names)
        return any(p in name for p in emulator_process_names)
    except psutil.NoSuchProcess:
        logging.warning("Process %s disappeared", process)

    return False


def kill_process_set(process_set) -> None:
    for process in process_set:
        if psutil.pid_exists(process.pid):
            try:
                logging.info("Terminating %s", process)
                kill_process_tree(process)
            except Exception as e:
                logging.warning(
                    "Failed to terminate %s due to %s", process, e, exc_info=e
                )


def kill_all_emulators(process_names):
    """Kills all running emulator or qemu-system processes."""
    process_set = [
        process
        for process in psutil.process_iter(["pid", "name"])
        if is_emulator_process(process, process_names)
    ]
    attempts = 3 if platform.system() != "Windows" else 6

    # This is the active set of emulator processes we could find.
    # We are going to kill every member of this set.
    # invariant is that len(process_set) will shrink..
    # We run this a few times to make sure we do not have any dangling zombies.
    while process_set and attempts > 0:
        kill_process_set(process_set)
        process_set = [
            process
            for process in psutil.process_iter(["pid", "name"])
            if is_emulator_process(process)
        ]
        attempts = attempts - 1

    if process_set:
        logging.warning("Unable to terminate %s", process_set)
    else:
        logging.info(">>>----- No emulator processes left! -----<<<")


def main():
    parser = argparse.ArgumentParser(
        usage="Terminates all running emulator and qemu-system-xxx processes",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        default=False,
        action="store_true",
        help=argparse.SUPPRESS,  # Suppress -v/--verbose from help
    )

    parser.add_argument(
        "--log-level",
        dest="log_level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level. Overrides --verbose.",
    )

    parser.add_argument(
        "-p",
        "--process_names",
        default="emulator, qemu-system, netsim, netsimd, netsimdx",
        help="Names of processes that should be killed",
    )

    args = parser.parse_args()

    lvl = logging.DEBUG if args.verbose else logging.WARNING
    if args.log_level:
        lvl = getattr(logging, args.log_level)

    message = "%(asctime)s %(message)s" if args.verbose else "%(message)s"

    logging.basicConfig(
        format=message,
        datefmt="%H:%M:%S",
        level=lvl,
    )
    kill_all_emulators(args.process_names)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.critical("Terminated by user")
        sys.exit(1)
    except Exception as exc:
        logging.critical("Failure during execution", exc_info=exc)
        sys.exit(1)
