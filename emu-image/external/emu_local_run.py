import errno
import sys
import os
import subprocess as sp

import emu_templates
from jinja2 import Environment, BaseLoader

if len(sys.argv) < 3:
    print("Usage: emu_local_run.py <emulator-dir-loc> <sysimg-dir-loc> [androidrootpath=.]")
    sys.exit(1)

androidrootpath = "."

if len(sys.argv) == 4:
    androidrootpath = sys.argv[3]

emu_dir = sys.argv[1]
img_dir = sys.argv[2]

print(emu_dir,img_dir,androidrootpath)

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

avd_dir = os.path.join(androidrootpath, "avd", "run.avd")
avd_ini_path = os.path.join(androidrootpath, "avd", "run.ini")
avd_config_ini_path = os.path.join(avd_dir, "config.ini")
sdk_dir = os.path.join(androidrootpath, "sdk")
sdk_platforms_dir = os.path.join(sdk_dir, "platforms")
sdk_platform_tools_dir = os.path.join(sdk_dir, "platform-tools")

img_dir_abspath = os.path.abspath(img_dir)

print("img abs path: %s" % img_dir_abspath)
print("avd ini path: %s" % avd_ini_path)
print("avd config ini path: %s" % avd_config_ini_path)

for d in [avd_dir, sdk_dir, sdk_platforms_dir, sdk_platform_tools_dir]:
    print("should mkdir %s" % d)
    mkdir_p(d)

avd_ini_template = Environment(loader=BaseLoader).from_string(emu_templates.avd_local_run_ini_template)
avd_config_ini_template = Environment(loader=BaseLoader).from_string(emu_templates.avd_local_run_config_ini_template)

with open(avd_ini_path, 'w') as avdinifile:
    avdinifile.write(
        avd_ini_template.render(
            avd_ini_path_rel=avd_dir,
            avd_ini_path=os.path.abspath(avd_dir)))

with open(avd_config_ini_path, 'w') as avdconfiginifile:
    avdconfiginifile.write(
        avd_config_ini_template.render(
            avd_config_ini_sysdir=img_dir_abspath))

print("Running: ANDROID_SDK_ROOT=%s/sdk ANDROID_SDK_HOME=%s %s/emulator -avd run -no-snapshot -show-kernel" % (androidrootpath, androidrootpath, emu_dir))

os.environ["ANDROID_SDK_ROOT"] = "%s/sdk" % androidrootpath
os.environ["ANDROID_SDK_HOME"] = "%s" % androidrootpath
sp.call("%s/emulator -avd run -no-snapshot -show-kernel" % emu_dir, shell=True)
