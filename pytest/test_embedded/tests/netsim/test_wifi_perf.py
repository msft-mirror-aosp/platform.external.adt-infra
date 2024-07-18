# Copyright 2024 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import logging
import re
import subprocess
import threading
import pytest


def _check_and_kill_iperf3_server():
  """Checks if port 5201 is in use and if an iperf3 server is running on localhost.

  If so, it logs a warning and attempts to kill the existing iperf3 process.
  """
  # Check if port 5201 is in use
  check_port_process = subprocess.run(
      [
          "lsof",
          "-i",
          "-P",
          "-n",
      ],
      capture_output=True,
      text=True,
  )
  for line in check_port_process.stdout.splitlines():
    if "5201" in line and "LISTEN" in line:
      logging.warning(f"Port 5201 is already in use:\n{line}")

  # Check for existing iperf3 server
  client_host_process = subprocess.run(
      ["iperf3", "-c", "localhost", "-t", "1"],
      capture_output=True,
      text=True,
      timeout=5,
  )

  if client_host_process.returncode == 0:
    logging.warning("An existing iperf3 server is already running.")
    pkill_process = subprocess.run(["pkill", "iperf3"])
    if pkill_process.returncode == 0:
      logging.info("Successfully killed existing iperf3 process.")
    else:
      logging.warning("Failed to kill existing iperf3 process.")


def _read_output(process, logger_name):
  logger = logging.getLogger(logger_name)
  while process.poll() is None:  # Check if the process is still running
    line = process.stdout.readline()
    if line:
      logger.info(line.rstrip())
  process.stdout.close()


@pytest.mark.wifi_perf
@pytest.mark.async_timeout(60 * 30)
async def test_iperf3(avd, record_property):
  """Test case to run iperf3 and record wifi performance."""
  # Disable cellular connection to make sure we are testing wifi
  await avd.adb.shell("svc data disable")
  which_iperf3_res = subprocess.run(
      ["which", "iperf3"], capture_output=True, text=True
  )
  if which_iperf3_res.returncode:
    logging.info(f"which iperf3 stdout: {which_iperf3_res.stdout}")
    logging.info(f"which iperf3 stderr: {which_iperf3_res.stderr}")
    assert False

  iperf3_version_res = subprocess.run(
      ["iperf3", "--version"], capture_output=True, text=True
  )
  logging.info(f"iperf3 --version stdout: {iperf3_version_res.stdout}")

  _check_and_kill_iperf3_server()

  # Run iperf server on host
  server_process = subprocess.Popen(
      ["iperf3 -s"],
      shell=True,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
  )
  threading.Thread(
      target=_read_output, args=(server_process, "iperf3_server"), daemon=True
  ).start()

  await asyncio.sleep(5)  # Wait a few seconds for iperf3 server to start

  # Run iperf client on host to make sure server is running
  client_host_process = subprocess.run(
      ["iperf3", "-c", "localhost", "-t", "3"], capture_output=True, text=True
  )

  if "error" in client_host_process.stdout:
    logging.info(f"client_host_process stdout: {client_host_process.stdout}")
    logging.info(f"client_host_process stderr: {client_host_process.stderr}")
    assert False

  # Run iperf client on guest
  result = await avd.adb.shell("iperf3 -c 10.0.2.2 -b 1000M -t 30", timeout=60)
  logging.info(f"iperf3 result: {result}")

  server_process.terminate()

  # Extract speeds by parsing iperf3 result
  speeds = re.findall(
      r"(\d+(\.\d+)*)\sMbits/sec", result, re.VERBOSE | re.DOTALL
  )

  if len(speeds) >= 2:
    sender_speed = speeds[-2]
    receiver_speed = speeds[-1]
    record_property("sender_speed", sender_speed)
    record_property("receiver_speed", receiver_speed)
  else:
    logging.warning(f"Failed to parse sender and receiver speeds from iperf3")
    assert False
