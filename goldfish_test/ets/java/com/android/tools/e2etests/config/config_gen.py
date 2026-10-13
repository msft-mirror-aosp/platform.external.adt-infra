"""Tool to generate tradefed configuration XML files.

Usage:
  config_gen.py <kind>

If a module has an empty list in EXCLUSIONS, it is excluded.
If a module has a non-empty list in EXCLUSIONS, only those tests are excluded.
All other tests are included.
"""

import enum
import os
import sys


class Kind(enum.Enum):
  PRESUBMIT = 1
  EMU_NOW = 2
  EMU_NOW_NO_DEQP = 3

ALL_MODULES = [
    "AdbPushPullTest",
    "AdbScreenCapTest",
    "AvdTest",
    "BatteryTest",
    "BootTest",
    "CallTest",
    "ClipboardTest",
    "ConnectivityTest",
    "ControlKeysTest",
    "DeqpRunnerTest",
    "DeviceHubUiTest",
    "DisplayNameTest",
    "FoldableDisplayTest",
    "InputTest",
    "MapsUiTest",
    "NetsimDaemonTest",
    "NetsimSingleDeviceTest",
    "ScreenshotTest",
    "SensorTest",
    "SmsTest",
    "SnapshotTest",
    "SnapshotUiTest",
    "TelnetTest",
    "VulkanAppTest",
    "WebGlAquariumUiTest",
]

# Maps Kind to a map of module name to a list of excluded test methods. If the
# list is empty, the entire module is excluded.
EXCLUSIONS = {
    Kind.PRESUBMIT: {
        # Needs an X display to run the Electron UI, which CI bots lack.
        "DeviceHubUiTest": [],
        "MapsUiTest": [],
        "SnapshotUiTest": [],
        "WebGlAquariumUiTest": [],
        # Needs a foldable AVD configuration (see //ets/foldable).
        "FoldableDisplayTest": [],
        # Not yet implemented on emu-next.
        "AvdTest": [],
        "CallTest": [],
        # Failing on emu-next.
        "ControlKeysTest": ["com.android.tools.e2etests.events.ControlKeysTest#screenshot"],
        # Not yet implemented on emu-next.
        "SnapshotTest": [],
        },
    Kind.EMU_NOW: {
        # Needs an X display to run the Electron UI, which CI bots lack.
        "DeviceHubUiTest": [],
        "MapsUiTest": [],
        "SnapshotUiTest": [],
        "WebGlAquariumUiTest": [],
        # Needs a foldable AVD configuration (see //ets/foldable).
        "FoldableDisplayTest": [],
        # These tests experience timeouts.
        "CallTest": [
            "com.android.tools.e2etests.call.CallTest#acceptCall",
            "com.android.tools.e2etests.call.CallTest#disconnectCall",
            "com.android.tools.e2etests.call.CallTest#takeCallOffHold",
            "com.android.tools.e2etests.call.CallTest#placeCallOnHold",
        ],
    },
}

EXCLUSIONS[Kind.EMU_NOW_NO_DEQP] = EXCLUSIONS[Kind.EMU_NOW] | {
    "DeqpRunnerTest": (),
    # TODO(b/570641589): Re-enable once Vulkan tests are fixed.
    "VulkanAppTest": [
        "com.android.tools.e2etests.vulkan.VulkanAppTest#testRunGears",
        "com.android.tools.e2etests.vulkan.VulkanAppTest#testRunGltfViewer",
        "com.android.tools.e2etests.vulkan.VulkanAppTest#testRunQrGenerator",
        "com.android.tools.e2etests.vulkan.VulkanAppTest#testRunTriangle",
        "com.android.tools.e2etests.vulkan.VulkanAppTest#testRunVulkanCapsViewer",
        "com.android.tools.e2etests.vulkan.VulkanAppTest#testRunVulkanSamplesHelloTriangle",
        "com.android.tools.e2etests.vulkan.VulkanAppTest#testRunVulkanSamplesHelloTriangle13",
        "com.android.tools.e2etests.vulkan.VulkanAppTest#testRunVulkanSamplesTextureLoading",
        "com.android.tools.e2etests.vulkan.VulkanAppTest#testRunVulkanSamplesDynamicUniformBuffers",
        "com.android.tools.e2etests.vulkan.VulkanAppTest#testRunVulkanSamplesComputeNbody",
        "com.android.tools.e2etests.vulkan.VulkanAppTest#testRunVulkanSamplesSynchronization2",
        "com.android.tools.e2etests.vulkan.VulkanAppTest#testRunVulkanSamplesSwapchainImages",
        "com.android.tools.e2etests.vulkan.VulkanAppTest#testRunVulkanSamplesSubpasses",
        "com.android.tools.e2etests.vulkan.VulkanAppTest#vulkanLavapipe",
    ],
}

HEADER = """
<configuration description="Presubmit tests">
    <include name="ets" />
"""

ENTRY = "    <option name=\"%s-filter\" value=\"%s\" />"

FOOTER = "</configuration>"


def main():
  if len(sys.argv) != 2:
    sys.stderr.write("Usage: python3 config_gen.py <kind>\n")
    os.exit(1)
  kind = Kind[sys.argv[1]]
  print(HEADER)
  for module in ALL_MODULES:
    exclusions = EXCLUSIONS[kind].get(module, None)
    if exclusions is None:
      print(ENTRY % ("include", module))
    elif len(exclusions) == 0:
      print(ENTRY % ("exclude", module))
    else:
      for test_method in exclusions:
        print(ENTRY % ("exclude", f"{module} {test_method}"))
  print(FOOTER)


if __name__ == "__main__":
  main()
