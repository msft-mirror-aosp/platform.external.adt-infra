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

# TODO(pprabhu) Update comment, convert to docstring.
# This is a standalone script to parse emulator boot test log files
# It does,
# 1. read log files, extract boot time information
# 2. dump avd configuration and boot time to csv file
# 3. upload csv data file and error file to big query table
# 4. upload log files to google storage bucket for long-term archive
# 5. remove log files from local disk
#
# This file should be placed under [LogDIR]\parser\,
# See site_config for site specific configuration required to use this script.

import bigquery
import bigquery_tables
import simple_parsers as sp
import site_config

import logging
import logging.handlers
import oauth2client.client as o2cclient
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile

# TODO(pprabhu) Clean this up. Include the image/revision specific information
# completely build.props file
_EMULATOR_BRANCHES = ["emu-master-dev", "emu-2.0-release"]
_API_TO_IMAGE_BRANCH = {
        '10': 'gb-emu-dev',
        '15': 'ics-mr1-emu-dev',
        '16': 'jb-emu-dev',
        '17': 'jb-mr1.1-emu-dev',
        '18': 'jb-mr2-emu-dev',
        '19': 'klp-emu-dev',
        '21': 'lmp-emu-dev',
        '22': 'lmp-mr1-emu-dev',
        '23': 'mnc-emu-dev',
        '24': 'nyc-emu-release',
}
def _get_branches(builder, file_path, api):
    for x in _EMULATOR_BRANCHES:
        if builder.endswith(x):
            emu_branch = x
            image_branch = 'sdk'
            return emu_branch, image_branch
    emu_branch = None
    if builder.endswith('system-image-builds'):
        emu_branch = 'sdk'
    else:
        for x in _EMULATOR_BRANCHES:
            if x in file_path:
                emu_branch = x
    image_branch = _API_TO_IMAGE_BRANCH.get(api) or 'Unknown'
    if (not emu_branch or (builder.endswith('cross-builds') and
        'boot_test_public_sysimage' in file_path)):
        logging.error('INVALID LOG...%s, skip ', file_path)
        return None, None
    return emu_branch, image_branch


_BOOT_TEST_LOG_RE = re.compile('.*boot_test.*/.*BootTestCase.*[^/]')
_BOOT_TEST_REGEXES = list(sp.AVD_REGEXES)
_BOOT_TEST_REGEXES += list(sp.BOOT_REGEXES)
_BOOT_TEST_REGEXES += list(sp.ADB_SPEED_REGEXES)
def _process_boot_test_logs(zip_path, bqt_boot_pass, bqt_boot_fail,
                            bqt_adb_speed):
    logging.info('Processing boot tests from |%s|.', zip_path)
    with zipfile.ZipFile(zip_path, 'r') as log_dir:
        log_files = [x for x in log_dir.namelist() if
                     _BOOT_TEST_LOG_RE.match(x)]
        if not log_files:
            # Found not boot test logs.
            return

        build_row = {}
        build_prop = sp.find_and_parse_build_prop(log_dir)
        build_row['builderName'] = (build_prop.get('buildername')
                                    .replace(' ', '_'))
        build_row['buildNumber'] = build_prop.get('buildnumber')

        for log_file in log_files:
            logging.info('Processing boot test log: |%s|' % log_file)
            boot_succeded = False
            boot_row = dict(build_row)
            adb_speed_row = None  # Only populated if speed was measured.
            with log_dir.open(log_file) as ifile:
                matches = sp.re_match_one_in_file(_BOOT_TEST_REGEXES, ifile)
                boot_row['api'] = matches.get(sp.AVD_API)
                boot_row['tag'] = matches.get(sp.AVD_TAG)
                boot_row['abi'] = matches.get(sp.AVD_ABI)
                boot_row['device'] = matches.get(sp.AVD_DEVICE)
                boot_row['ram'] = matches.get(sp.AVD_RAM)
                boot_row['gpu'] = matches.get(sp.AVD_GPU)
                boot_row['qemu'] = matches.get(sp.AVD_QEMU_ENGINE)

                emu_branch, image_branch = _get_branches(
                        build_row['builderName'], log_file, boot_row['api'])
                if emu_branch is None or image_branch is None:
                    pass
                boot_row['emu_branch'] = emu_branch
                boot_row['image_branch'] = image_branch
                boot_row['emu_revision'] = build_prop.get(emu_branch) or 'sdk'
                boot_row['image_revision'] = (
                        build_prop.get('git_' + image_branch) or
                        build_prop.get(image_branch) or 'sdk')

                # ADB speed row is identical so far.
                if (matches.get(sp.ADB_PUSH_SPEED) or
                    matches.get(sp.ADB_PULL_SPEED)):
                    adb_speed_row = dict(boot_row)
                    adb_speed_row['push_speed'] = matches.get(sp.ADB_PUSH_SPEED)
                    adb_speed_row['pull_speed'] = matches.get(sp.ADB_PULL_SPEED)

                if sp.BOOT_TIMEOUT in matches:
                    boot_row['boottime'] = 0.0
                elif (sp.BOOT_FAIL in matches or
                      matches.get(sp.BOOT_TIME) is None):
                    boot_row['boottime'] = 9999
                else:
                    boot_row['boottime'] = matches[sp.BOOT_TIME]
                    boot_succeded = True

                if boot_succeded:
                    bqt_boot_pass.append_row(boot_row)
                else:
                    bqt_boot_fail.append_row(boot_row)
                if adb_speed_row is not None:
                    bqt_adb_speed.append_row(adb_speed_row)


def _gs_offloader(zip_path, is_prod):
    with zipfile.ZipFile(zip_path) as log_dir:
        build_prop = sp.find_and_parse_build_prop(log_dir)
    slave = build_prop['buildername'].replace(' ', '_')
    dst_path = 'gs://emu_test_traces/%s/' % slave
    logging.debug('Uploading file to Google Storage - %s to %s ',
                  zip_path, dst_path)
    cmd = ['/home/user/bin/gsutil', 'mv', zip_path, dst_path]
    if is_prod:
        subprocess.check_call(cmd)
    else:
        logging.info('NO-PROD: Skipped command: %s' % str(cmd))


_LOG_DIR_RE = re.compile('build_(\d+)-rev_(.*).zip')
def _for_each_slave_run(root_dir, steps):
    """Run each processing step on each of the zipped logs from the slaves.

    Args:
        root_dir: Directory containing the slave specific logs.
        steps: A list of steps to perform in order. Each step is a functor
                taking a single argument for the root directory of logs for a
                given run.
    """
    for slave in os.listdir(root_dir):
        logging.info('Processing logs from slave: %s' % slave)
        slave_dir = os.path.join(root_dir, slave)
        if os.path.isdir(slave_dir):
            runs = [x for x in os.listdir(slave_dir) if _LOG_DIR_RE.match(x)]
            for run in runs:
                zip_path = os.path.join(slave_dir, run)
                for step in steps:
                    step(zip_path)


def _backup_logs(workdir, backupdir):
    dst = os.path.join(backupdir,
                       'work_%s' % time.strftime('%Y%m%d-%H%M%S'))
    shutil.make_archive(dst, 'gztar', workdir, workdir)


_TABLE_DATA = 'avd_to_time_data'
_TABLE_ERR = 'avd_to_time_error'
_TABLE_ADB = 'avd_to_adb_speed'
def main(args):
    cwd = os.path.dirname(os.path.realpath(__file__))
    config = site_config.setup(cwd)

    # All logs are found inside this directory
    slave_logs_dir = os.path.join(cwd, '..')
    # Any local files you write must be inside this directory.
    # Avoids polluting current directory, and allows easy backup.
    workdir = os.path.join(cwd, 'workdir')
    # Scary!
    shutil.rmtree(workdir, ignore_errors=True)
    os.mkdir(workdir)
    # In case of failure, any files created and logs are backed up here.
    backupdir = os.path.join(cwd, 'log_backups')
    try:
        os.mkdir(backupdir)
    except OSError:
        # Directory exists.
        pass
    # Otherwise, we back them up anyway, here.
    goodrunsdir = os.path.join(cwd, 'finished_runs')
    try:
        os.mkdir(goodrunsdir)
    except OSError:
        # Directory exists.
        pass

    log_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s')
    file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(workdir, 'parser_logs.txt'),
            maxBytes=1048576, backupCount=10)
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.DEBUG)

    # Add our custom handlers to the root logger.
    logger = logging.getLogger()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.setLevel(logging.DEBUG)

    bq = bigquery.BigQuery(
            config[site_config.GCLOUD_PROJECT_ID],
            config[site_config.GCLOUD_BQ_DATASET_ID],
            o2cclient.GoogleCredentials.get_application_default())
    bqt_boot_pass = bigquery_tables.BootTimeTable(
            os.path.join(workdir, 'AVD_to_time_data.csv'))
    bqt_boot_fail = bigquery_tables.BootTimeTable(
            os.path.join(workdir, 'AVD_to_time_error.csv'))
    bqt_adb_speed = bigquery_tables.AdbSpeedTable(
            os.path.join(workdir, 'AVD_to_adb_speed.csv'))

    try:
        _for_each_slave_run(slave_logs_dir,
                            [(lambda x: _process_boot_test_logs(x,
                                                                bqt_boot_pass,
                                                                bqt_boot_fail,
                                                                bqt_adb_speed)),
                             # Must be last as it removes the zip file.
                             (lambda x: _gs_offloader(
                                     x, config[site_config.IS_PROD]))])
        bq.upload(bqt_boot_pass, _TABLE_DATA)
        bq.upload(bqt_boot_fail, _TABLE_ERR)
        bq.upload(bqt_adb_speed, _TABLE_ADB)
        _backup_logs(workdir, goodrunsdir)
    except:
        # First, forcibly log the exception so that it appears in our log file.
        logging.exception('TOP LEVEL EXCEPTION')

        try:
            _backup_logs(workdir, backupdir)
        except:
            logging.warning('Backup failed after earlier error. '
                            'Failed to archive %s to %s' %
                            (workdir, backupdir))
        # Always re-raise the catch-all exception.
        raise


if __name__ == '__main__':
    main(sys.argv)
