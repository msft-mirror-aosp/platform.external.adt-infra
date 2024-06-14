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
import pytest


@pytest.mark.wifi_perf
@pytest.mark.async_timeout(60 * 30)
async def test_iperf3(avd, record_property):
  """Test case to run iperf3 and record wifi performance."""
  # Disable cellular connection to make sure we are testing wifi
  await avd.adb.shell("svc data disable")
  # Run iperf server on host
  subprocess.Popen(
      ["iperf3", "-s"],
      shell=True,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
  )
  await asyncio.sleep(5)  # Wait a few seconds for iperf3 server to start

  # Run iperf client on guest
  result = await avd.adb.shell("iperf3 -c 10.0.2.2 -b 1000M -t 30", timeout=60)
  logging.info(f"iperf3 result: {result}")

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
