import os
from pathlib import Path

# APKS that are not part of the prebuilt packages.
_DATA_DIR = Path(os.path.dirname(__file__))
APP_DEBUG_APK = _DATA_DIR / "app-debug.apk"
APP_MOBLY_APK = _DATA_DIR / "mobly-bundled-snippets-debug.apk"

# Prebuilt packages are stored in a well known location in the user's home directory.
_PREBUILT_DIR = Path(os.path.expanduser('~')) / "builds/apps"

# By default we point to the locally available APKs
APP_HELLOVK_APK = _DATA_DIR / "hellovk.apk"
APP_GEARS_APK = _DATA_DIR / "gears-debug.apk"
APP_GLTF_VIEWER_APK = _DATA_DIR / "gltf-viewer.apk"
APP_MAPS_DEMO_APK = _DATA_DIR / "maps_demo.apk"
APP_TRIANGLE_APK = _DATA_DIR / "triangle-debug.apk"
APP_VULKANCAPSVIEWER_APK = _DATA_DIR / "vulkancapsviewer_3.40_arm.apk"
APP_VULKAN_SAMPLES_APK = _DATA_DIR / "vulkan_samples-release.apk"
APP_VULKAN_SAMPLES_ASSETS = _DATA_DIR / "assets" / "vulkan_samples"
APP_GFXBENCH_APK = _DATA_DIR / "gfxbench_vulkan-5.1.5+corporate.apk"
APP_GFXBENCH_ASSETS = _DATA_DIR / "assets" / "gfxbench"
APP_QR_GENERATOR_APK = _DATA_DIR / "qr-generator.apk"

# The prebuilt versions of the APKs are stored in a zip file.
PREBUILT_HELLOVK_APK = _PREBUILT_DIR / "hellovk/hellovk/hellovk.apk"
PREBUILT_GEARS_APK = _PREBUILT_DIR / "gears/gears/gears-debug.apk"
PREBUILT_GLTF_VIEWER_APK = _PREBUILT_DIR / "gltf-viewer/gltf-viewer/gltf-viewer.apk"
PREBUILT_MAPS_DEMO_APK = _PREBUILT_DIR / "maps_demo/maps_demo/maps_demo.apk"
PREBUILT_TRIANGLE_APK = _PREBUILT_DIR / "triangle/triangle/triangle-debug.apk"
PREBUILT_VULKANCAPSVIEWER_APK = _PREBUILT_DIR / "vulkancapsviewer/vulkancapsviewer/vulkancapsviewer_3.40_arm.apk"
PREBUILT_VULKAN_SAMPLES_DIR = _PREBUILT_DIR / "vulkan_samples/vulkan_samples"
PREBUILT_QR_GENERATOR_APK = _PREBUILT_DIR / "qr-generator/qr-generator/qr-generator.apk"
PREBUILT_VULKAN_SAMPLES_APK = PREBUILT_VULKAN_SAMPLES_DIR / "vulkan_samples-release.apk"
PREBUILT_VULKAN_SAMPLES_ASSETS = PREBUILT_VULKAN_SAMPLES_DIR
PREBUILT_GFXBENCH_DIR = _PREBUILT_DIR / "gfxbench/"
PREBUILT_GFXBENCH_APK = PREBUILT_GFXBENCH_DIR / "gfxbench_vulkan-5.1.5+corporate.apk"
PREBUILT_GFXBENCH_ASSETS = PREBUILT_GFXBENCH_DIR
