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

import json
import logging
import os
import pprint
import time
from apiclient import http
from googleapiclient import discovery


class BigQueryException(Exception):
    """Any intelligible exception from this module."""


class BigQuery(object):
    """Client object to interact with a BigQuery dataset

    Default values are set for a test dataset. Bots should override this.
    """

    DEFAULT_PROJECT_ID = 'android-devtools-emulator'
    DEFAULT_DATASET_ID = 'emu_buildbot_test'

    def __init__(self, project_id=None, dataset_id=None, credentials=None):
        assert credentials is not None
        if project_id is not None:
            self._project_id = project_id
        else:
            self._project_id = self.DEFAULT_PROJECT_ID
        if dataset_id is not None:
            self._dataset_id = dataset_id
        else:
            self._dataset_id = self.DEFAULT_DATASET_ID

        self._bigquery = discovery.build('bigquery', 'v2',
                                         credentials=credentials)

    def upload(self, bq_table, table_id):
        """Uploads data from GenericBigQueryTable |bq_tale| to |table_id|.

        Skips empty files.
        """
        bq_table.flush()
        for data_path in bq_table.backing_files:
            self._upload_one(bq_table, data_path, table_id)

    def _upload_one(self, bq_table, data_path, table_id):
        """The engine behind |upload|."""
        schema_path = bq_table.schema_path
        logging.info('Uploading data to (project:%s, datatset:%s, table:%s) '
                     'from %s with schema %s' % (
                             self._project_id, self._dataset_id, table_id,
                             data_path, schema_path))

        if os.stat(data_path).st_size == 0:
            logging.info('No data found. Skipping upload.')
            return

        source_format = ('CSV' if bq_table.source_format == bq_table.FORMAT_CSV
                         else 'NEWLINE_DELIMITED_JSON')

        # Post to the jobs resource using the client's media upload interface.
        # See:
        # http://developers.google.com/api-client-library/
        #         python/guide/media_upload
        insert_request = self._bigquery.jobs().insert(
            projectId=self._project_id,
            # Provide a configuration object. See:
            # https://cloud.google.com/bigquery/docs/reference/v2/jobs#resource
            body={
                'configuration': {
                    'load': {
                        'schema': {
                            'fields': json.load(open(schema_path, 'r'))
                        },
                        'destinationTable': {
                            'projectId': self._project_id,
                            'datasetId': self._dataset_id,
                            'tableId': table_id
                        },
                        'sourceFormat': source_format,
                    }
                }
            },
            media_body=http.MediaFileUpload(
                data_path,
                mimetype='application/octet-stream'))
        job = insert_request.execute()

        logging.info('Waiting for job to finish...')
        status_request = self._bigquery.jobs().get(
            projectId=job['jobReference']['projectId'],
            jobId=job['jobReference']['jobId'])

        # Poll the job until it finishes.
        while True:
            result = status_request.execute(num_retries=2)
            status = result['status']
            if status['state'] == 'DONE':
                if 'errorResult' in status:
                    err = ('Error when updating table %s with rows from %s '
                           'using schema %s' % (table_id, data_path,
                                                schema_path))
                    logging.error(err)
                    logging.error('BigQuery error details:')
                    logging.error(pprint.pformat(status['errorResult']))
                    raise BigQueryException(err)
                else:
                    logging.info('Job complete.')
                    return

            time.sleep(1)
