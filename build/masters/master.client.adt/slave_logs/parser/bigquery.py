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

import collections
import json
import logging
import os
import pprint
import threading
import time
from apiclient import http
from googleapiclient import discovery


class BigQueryException(Exception):
    """Any intelligible exception from this module."""

_Context = collections.namedtuple(
        '_Context',
        ['lock', 'bigquery', 'project_id', 'dataset_id', 'table_id',
         'data_format', 'schema_path'])
_UploadItem = collections.namedtuple(
        '_UploadItem',
        ['context', 'data_path'])


def _upload_one(item):
    """The engine behind |BigQuery.upload|.

    Args:
        item: An _UploadItem to upload.
    """
    context = item.context
    logging.debug('Uploading data to (project:%s, datatset:%s, table:%s) '
                  'from %s with schema %s' %
                  (context.project_id, context.dataset_id, context.table_id,
                   item.data_path, context.schema_path))
    size = os.stat(item.data_path).st_size
    if size == 0:
        logging.info('No data found. Skipping upload.')
        return
    if size > 10 * 1024 * 1024:
        logging.error('File to upload too large (%s MB). '
                      'BigQuery limit is 10 MB. Upload will likely fail.' %
                      (size,))

    # Post to the jobs resource using the client's media upload interface.
    # See:
    # http://developers.google.com/api-client-library/
    #         python/guide/media_upload

    # Provide a configuration object. See:
    # https://cloud.google.com/bigquery/docs/reference/v2/jobs#resource
    body = {
        'configuration': {
            'load': {
                'schema': {
                    'fields': json.load(open(context.schema_path, 'r'))
                },
                'destinationTable': {
                    'projectId': context.project_id,
                    'datasetId': context.dataset_id,
                    'tableId': context.table_id
                },
                'sourceFormat': context.data_format,
            }
        }
    }
    media_body = http.MediaFileUpload(
        item.data_path,
        mimetype='application/octet-stream')

    with context.lock:
        insert_request = context.bigquery.jobs().insert(
            projectId=context.project_id,
            body=body,
            media_body=media_body)
        job = insert_request.execute()
        status_request = context.bigquery.jobs().get(
            projectId=job['jobReference']['projectId'],
            jobId=job['jobReference']['jobId'])

    # Poll the job until it finishes.
    while True:
        with context.lock:
            result = status_request.execute(num_retries=2)
        status = result['status']
        if status['state'] == 'DONE':
            if 'errorResult' in status:
                err = ('Error when updating table %s with rows from %s '
                        'using schema %s' % (context.table_id, item.data_path,
                                             context.schema_path))
                logging.error(err)
                logging.error('BigQuery error details:')
                logging.error(pprint.pformat(status['errorResult']))
                raise BigQueryException(err)
            else:
                return
        time.sleep(1)


class BigQuery(object):
    """Client object to interact with a BigQuery dataset

    Default values are set for a test dataset. Bots should override this.
    """

    NUM_CONCURRENT_UPLOADS = 20
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
        data_format = ('CSV' if bq_table.source_format == bq_table.FORMAT_CSV
                       else 'NEWLINE_DELIMITED_JSON')
        context = _Context(
                threading.Lock(), self._bigquery, self._project_id,
                self._dataset_id, table_id, data_format, bq_table.schema_path)
        items = [_UploadItem(context, x) for x in bq_table.backing_files]
        threads = [threading.Thread(target=_upload_one,
                                    args=(i,))
                   for i in items]
        done = 0
        while threads:
            concurrency = min(self.NUM_CONCURRENT_UPLOADS, len(threads))
            logging.info(
                    'Starting next batch of %d threads to upload files: %s' %
                    (concurrency,
                     [x.data_path for x in items[done:done+concurrency]]))
            for i in range(concurrency):
                threads[i].start()
            for i in range(concurrency):
                threads[i].join()
            threads = threads[concurrency:]
            done += concurrency
        logging.info('Upload complete.')
