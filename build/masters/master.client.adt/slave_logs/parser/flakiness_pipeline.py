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

import bigquery
import bigquery_tables
import simple_parsers as sp
import site_config

import datetime
import logging
import logging.handlers
import oauth2client.client as o2cclient
import os
import os.path
import pprint
import shutil
import sys
import time


class FlakinessPipline(object):
    """A class that encapsulates the BigQuery pipeline for flakiness data."""

    TABLE_STEPS = 'steps'

    TAG_TRANSITION = 'transition'

    STATE_STARTED = 'started'
    STATE_FINISHED = 'finished'

    QUERY_NOW = """
    SELECT FORMAT_UTC_USEC(NOW())
    """
    QUERY_GET_STEPS = """
    SELECT
        FORMAT_UTC_USEC(timestamp) as timestamp, tag, state
    FROM
        DATASET_ID.{TABLE_STEPS}
    """

    def __init__(self, bigquery, bigquery_ws, workdir):
        self._bigquery = bigquery
        self._bigquery_ws = bigquery_ws
        self._workdir = workdir

    def run(self):
        self._sync_time()
        self._transition_start()
        old_steps = self._query_current_steps()
        new_steps = self._take_actions(old_steps)
        self._transition_commit(new_steps)

    def _flatten(self, query):
        return query.format(
                TABLE_STEPS=self.TABLE_STEPS)

    def _sync_time(self):
        schema = [{
                'name': 'timestamp',
                'type': 'timestamp',
                'mode': 'required'
        }]
        self._remote_now = self._bigquery.sync_query(
                self._flatten(self.QUERY_NOW), schema)[0]['timestamp']
        self._local_now = datetime.datetime.utcnow()

    def _synced_now(self):
        diff = datetime.datetime.utcnow() - self._local_now
        return self._remote_now + diff

    def _transition_start(self):
        table_steps = bigquery_tables.PipelineSteps(self._workdir)
        table_steps.append_row({
                'timestamp': sp.bq_format_timestamp(self._synced_now()),
                'tag': self.TAG_TRANSITION,
                'state': self.STATE_STARTED
        })
        self._bigquery_ws.upload(table_steps, self.TABLE_STEPS)

    def _transition_commit(self, new_steps):
        table_steps = bigquery_tables.PipelineSteps(self._workdir)
        for step in new_steps:
            table_steps.append_row(step)
        table_steps.append_row({
                'timestamp': sp.bq_format_timestamp(self._synced_now()),
                'tag': self.TAG_TRANSITION,
                'state': self.STATE_FINISHED
        })
        self._bigquery_ws.upload(table_steps, self.TABLE_STEPS)

    def _query_current_steps(self):
        return self._bigquery_ws.sync_query(
                self._flatten(self.QUERY_GET_STEPS),
                bigquery_tables.PipelineSteps.SCHEMA_PATH)

    def _take_actions(self, old_steps):
        pprint.pprint(old_steps)
        return []


def _try_make_dir(dirname):
    try:
        os.mkdir(dirname)
    except OSError:
        # Directory exists.
        pass


def _backup_logs(workdir, backupdir):
    dst = os.path.join(backupdir,
                       'work_%s' % time.strftime('%Y%m%d-%H%M%S'))
    shutil.make_archive(dst, 'gztar', workdir, workdir)


def main(args):
    cwd = os.path.dirname(os.path.realpath(__file__))
    config = site_config.setup(cwd)

    # Any local files you write must be inside this directory.
    # Avoids polluting current directory, and allows easy backup.
    workdir = os.path.join(cwd, 'pipline_workdir')
    # Scary!
    shutil.rmtree(workdir, ignore_errors=True)
    os.mkdir(workdir)
    # In case of failure, any files created and logs are backed up here.
    backupdir = os.path.join(cwd, 'pipeline_backups')
    _try_make_dir(backupdir)
    # Otherwise, we back them up anyway, here.
    goodrunsdir = os.path.join(cwd, 'pipline_finished')
    _try_make_dir(goodrunsdir)

    log_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s')
    file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(workdir, 'main_log.txt'),
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
    bq_ws = bigquery.BigQuery(
            config[site_config.GCLOUD_PROJECT_ID],
            config[site_config.GCLOUD_BQ_WORKSPACE_DATASET_ID],
            o2cclient.GoogleCredentials.get_application_default())

    try:
        pipeline = FlakinessPipline(bq, bq_ws, workdir)
        pipeline.run()
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
