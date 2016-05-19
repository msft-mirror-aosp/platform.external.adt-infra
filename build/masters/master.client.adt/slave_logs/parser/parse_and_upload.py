# Copyright 2016 The Android Open Source Project
#
# This software is licensed under the terms of the GNU General Public
# License version 2, as published by the Free Software Foundation, and
# may be copied, distributed, and modified under those terms.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# This is a standalone script to parse emulator boot test log files
# It does,
# 1. read log files, extract boot time information
# 2. dump avd configuration and boot time to csv file
# 3. upload csv data file and error file to big query table
# 4. upload log files to google storage bucket for long-term archive
# 5. remove log files from local disk
#
# This file should be placed under [LogDIR]\parser\,
# BigQuery schema should be placed under the same directory and named "boot_time_csv_schema.json"
# The script also assume client secret file "LLDB_BUILD_SECRETS.json" exists under the same directory

import bigquery

import os
import re
import argparse
import json
import time
import zipfile
import subprocess
import logging
import traceback
from logging.handlers import RotatingFileHandler
from oauth2client.client import GoogleCredentials

from time import gmtime, strftime
from shutil import copyfile

project_id = 'android-devtools-lldb-build'
dataset_id = 'emu_buildbot'

table_data = 'avd_to_time_data'
table_err = 'avd_to_time_error'
table_adb = 'avd_to_adb_speed'

parser_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.join(parser_dir, "..")

file_data = os.path.join(parser_dir, "AVD_to_time_data.csv")
file_err = os.path.join(parser_dir, "AVD_to_time_error.csv")
file_adb = os.path.join(parser_dir, "AVD_to_adb_speed.csv")
boot_schema_path = os.path.join(parser_dir, "boot_time_csv_schema.json")
adb_schema_path = os.path.join(parser_dir, "adb_csv_schema.json")

result_re = re.compile(".*AVD (.*), boot time: (\d*.?\d*), expected time: \d+")
log_dir_re = re.compile("build_(\d+)-rev_(.*).zip")
avd_re = re.compile("([^-]*)-(.*)-(.*)-(\d+)-gpu_(.*)-api(\d+)")
avd_android_re = re.compile("([^-]*-[^-]*)-(.*)-(.*)-(\d+)-gpu_(.*)-api(\d+)")
start_re = re.compile(".*INFO - Running - (.*)")
timeout_re = re.compile(".*ERROR - AVD (.*) didn't boot up within (\d+) seconds")
fail_re = re.compile("^FAIL: test_boot_(.*)_qemu(\d+) \(test_boot.test_boot.BootTestCase\)$")
adb_result_re = re.compile(".*- INFO - AVD (.*), adb push: (\d+) KB/s, adb pull: (\d+) KB/s")

log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = RotatingFileHandler(os.path.join(parser_dir, "parser_logs.txt"), maxBytes=1048576, backupCount=10)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.DEBUG)

logger = logging.getLogger()
logger.addHandler(file_handler)
logger.addHandler(console_handler)
logger.setLevel(logging.DEBUG)

emulator_branches = ["emu-master-dev", "emu-2.0-release"]
api_to_image_branch = {
                       '10':'gb-emu-dev',
                       '15':'ics-mr1-emu-dev',
                       '16':'jb-emu-dev',
                       '17':'jb-mr1.1-emu-dev',
                       '18':'jb-mr2-emu-dev',
                       '19':'klp-emu-dev',
                       '21':'lmp-emu-dev',
                       '22':'lmp-mr1-emu-dev',
                       '23':'mnc-emu-dev',
                       '24':'nyc-emu-release',
                      }

def get_branches(builder, file_path, api):
  print "inside: ", builder, file_path, api
  for x in emulator_branches:
    if builder.endswith(x):
        emu_branch = x
        image_branch = "sdk"
        return emu_branch, image_branch
  emu_branch = None
  if builder.endswith("system-image-builds"):
    emu_branch = "sdk"
  else:
    for x in emulator_branches:
      if x in file_path:
        emu_branch = x
  image_branch = api_to_image_branch.get(api) or "Unknown"
  if not emu_branch or (builder.endswith("cross-builds") and "boot_test_public_sysimage" in file_path):
     logging.error("INVALID LOG...%s, skip ", file_path)
     return None, None
  return emu_branch, image_branch

def get_props(zip_path):
  try:
    with zipfile.ZipFile(zip_path, 'r') as log_dir:
      for log_file in log_dir.namelist():
        if log_file.endswith('build.props'):
          with log_dir.open(log_file) as f:
            return json.load(f)
  except:
    logging.error(traceback.format_exc())
    return {}

# process a zip folder
def process_zipfile(zip_name, builder, csv_data, csv_err, csv_adb):
    zip_path = os.path.join(root_dir, builder, zip_name)
    logger.info("Process zip file %s", zip_name)
    if log_dir_re.match(zip_name):
        build, revision = log_dir_re.match(zip_name).groups()
    else:
        logger.info("Skip invalid directory %s", zip_name)
        return
    props = get_props(zip_path)
    with zipfile.ZipFile(zip_path, 'r') as log_dir:
        for x in [log_file for log_file in log_dir.namelist() if not log_file.endswith('/')]:
            if any(s in x for s in ["CTS_test", "verbose", "logcat"]):
                continue
            #logger.info("parsing file %s ...", log_path)
            with log_dir.open(x) as f:
                for line in f:
                    is_timeout = False
                    is_fail = False
                    is_adb_result = False
                    if start_re.match(line):
                        if "_qemu2" in line:
                            is_qemu2 = True
                        else:
                            is_qemu2 = False
                    if timeout_re.match(line):
                        is_timeout = True
                    elif fail_re.match(line):
                        is_fail = True
                    elif adb_result_re.match(line):
                        is_adb_result = True
                    gr = result_re.match(line)
                    if gr is not None or any([is_timeout, is_fail, is_adb_result]):
                        if is_timeout:
                            boot_time = 9999
                            avd = timeout_re.match(line).groups()[0]
                            result_file = csv_err
                        elif is_fail:
                            boot_time = 0.0
                            avd = fail_re.match(line).groups()[0]
                            is_qemu2 = (fail_re.match(line).groups()[1] == "2")
                            result_file = csv_err
                        elif is_adb_result:
                            avd, push_speed, pull_speed = adb_result_re.match(line).groups()
                            result_file = csv_adb
                        else:
                            avd, boot_time = gr.groups()
                            result_file = csv_data
                        if any([t in avd for t in ["android-wear", "android-tv"]]):
                            tag, abi, device, ram, gpu, api = avd_android_re.match(avd).groups()
                        else:
                            tag, abi, device, ram, gpu, api = avd_re.match(avd).groups()
                        emu_branch, image_branch = get_branches(builder, x, api)
                        if None in [emu_branch, image_branch]:
                            continue
                        emu_revision = props.get(emu_branch) or "sdk"
                        image_revision = props.get("git_" + image_branch) or props.get(image_branch) or "sdk"
                        if is_adb_result:
                            record_line = "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % (api, tag, abi, device, ram, gpu, "qemu2" if is_qemu2 else "qemu1", builder, build, emu_revision, image_revision, push_speed, pull_speed, emu_branch, image_branch)
                        else:
                            record_line = "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % (api, tag, abi, device, ram, gpu, "qemu2" if is_qemu2 else "qemu1", builder, build, emu_revision, image_revision, boot_time, emu_branch, image_branch)
                        result_file.write(record_line)
    dst_path = "gs://emu_test_traces/%s/" % builder
    logger.info("upload file to Google Storage - %s to %s ", zip_path, dst_path)
    subprocess.check_call(["/home/user/bin/gsutil", "mv", zip_path, dst_path])

def parse_logs():
    """Parse zipped log files and write to file in csv format"""

    with open(file_data, 'w') as csv_data, open(file_err, 'w') as csv_err, open(file_adb, 'w') as csv_adb:
        for x in os.listdir(root_dir):
            builder = x
            logger.info("Builder: %s", builder)
            builder_dir = os.path.join(root_dir, builder)
            if os.path.isdir(builder_dir):
                for zip_dir in [x for x in os.listdir(builder_dir) if x.endswith(".zip")]:
                    process_zipfile(zip_dir, builder, csv_data, csv_err, csv_adb)

if __name__ == "__main__":
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(parser_dir, "LLDB_BUILD_SECRETS.json")

    def back_up():
        for x in [file_data, file_err, file_adb]:
            dst = "%s_%s" % (x, strftime("%Y%m%d-%H%M%S"))
            copyfile(x, dst)
    try:
        logging.info("Start log parser ...")
        parse_logs()
    except:
        logging.info(traceback.format_exc())
        back_up()
        exit(0)
    try:
        bq = bigquery.BigQuery(
                project_id, dataset_id,
                GoogleCredentials.get_application_default())
        bq.upload(boot_schema_path, file_data, table_data)
        bq.upload(boot_schema_path, file_err, table_err)
        bq.upload(adb_schema_path, file_adb, table_adb)
    except:
        logging.info(traceback.format_exc())
        back_up()
