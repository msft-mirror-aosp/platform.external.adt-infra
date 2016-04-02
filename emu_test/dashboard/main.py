import logging
import os
import cgi
from oauth2client.appengine import oauth2decorator_from_clientsecrets
import webapp2

import json
import bqclient
from gviz_data_table import encode
from gviz_data_table import Table

from google.appengine.api import memcache
from google.appengine.ext.webapp.template import render

import httplib2
from oauth2client.appengine import AppAssertionCredentials
credentials = AppAssertionCredentials(scope='https://www.googleapis.com/auth/bigquery')
http = credentials.authorize(httplib2.Http(memcache))

# Project ID for a project where you and your users
# are viewing members.  This is where the bill will be sent.
# During the limited availability preview, there is no bill.
# Replace this value with the Client ID value from your project,
# the same numeric value you used in client_secrets.json
BILLING_PROJECT_ID = "64975201253"
DATA_PROJECT_ID = "android-devtools-lldb-build"
DATASET = "emu_buildbot"
TABLE_DATA = "avd_to_time_data"
TABLE_ERROR = "avd_to_time_error"
TABLE_ADB = "avd_to_adb_speed"
mem = memcache.Client()

def get_query_clause(vars):
    gpu_val = {"on": "yes",
               "off": "no",
               "mesa": "mesa"}

    def get_select_clause(columns):
        """ columns should be a dictionary with column name as key and description in title as value"""

        select_clause = ""
        for host in vars['HOST']:
            for tag in vars['TAG']:
                for gpu in vars['GPU']:
                    for qemu in  vars['QEMU']:
                        for k, v in columns.iteritems():
                            select_clause += "last (CASE WHEN (builderName = '%s' AND tag = '%s' AND gpu = '%s' AND qemu = '%s') THEN %s ELSE null END) AS [%s_%s_%s_%s%s], " % (host, tag, gpu_val[gpu], qemu, k, host.replace('-', '_'), tag.replace('-', '_'), gpu, qemu, v)
        return select_clause

    where_clause = "api = %s AND abi = '%s'" % (vars['API'][0], vars['ABI'][0])
    QUERY = ("SELECT "
             "revision AS build, "
             "%s"
             "FROM [%s:%s.%s] "
             "WHERE %s "
             "group by build order by build") % (get_select_clause({"boottime": ""}), DATA_PROJECT_ID, DATASET, TABLE_DATA, where_clause)
    logging.info(QUERY)
    title = "AVD - api: %s, abi: %s, tag: %s, gpu: %s, qemu: %s" % ('/'.join(vars['API']), '/'.join(vars['ABI']), '/'.join(vars['TAG']), '/'.join(vars['GPU']), '/'.join(vars['QEMU']))

    sum_where = where_clause + " AND (builderName = '" + "' OR builderName = '".join(vars['HOST']) + "')"
    SUM_QUERY = ("SELECT "
                 "builderName AS builder, "
                 "AVG(boottime) as avg_time, "
                 "NTH(501, quantiles(boottime, 1001)) as median, "
                 "FROM [%s:%s.%s] "
                 "WHERE %s "
                 "group by builder order by avg_time") % (DATA_PROJECT_ID, DATASET, TABLE_DATA, sum_where)
    #logging.info(SUM_QUERY)

    ADB_QUERY = ("SELECT "
                 "revision AS build, "
                 "%s"
                 "FROM [%s:%s.%s] "
                 "WHERE %s "
                 "group by build order by build") % (get_select_clause({"push_speed": "_push", "pull_speed": "_pull"}), DATA_PROJECT_ID, DATASET, TABLE_ADB, where_clause)
    logging.info(ADB_QUERY)

    return title, QUERY, SUM_QUERY, ADB_QUERY


def bq2table(bqdata):
    def getType(type_str):
        if type_str == "INTEGER":
            return int
        elif type_str == "FLOAT":
            return float
        elif type_str == "STRING":
            return str
        else:
            return eval(type_str)
    table = Table()
    for x in bqdata["schema"]["fields"]:
        table.add_column(x["name"], getType(x["type"]), x["name"])
    if "rows" in bqdata:
        for row in bqdata["rows"]:
            row_data = []
            for x,t in zip(row["f"], bqdata["schema"]["fields"]):
                val = getType(t["type"])(x["v"] or 0)
                if t["type"] == "FLOAT":
                    val = float("{0:.2f}".format(val))
                row_data.append(val)
            table.append(row_data)
    count = len(table.rows)
    logging.info("FINAL BOOTTIMEDATA---")
    return count, encode(table)

class MainPage(webapp2.RequestHandler):
    def get(self):

        template_data = {'table_bootdata': 0,
                'table_adbdata': 0,
                'table_sumdata': 0,
                'table_title': 0,
                'table_row_count': 0,
                'query_complete': 0,
                'paint_vars': json.dumps({}),
                'query': ''}
        if len(self.request.GET) != 0:
            paint_vars = {}
            for col_name in ['HOST', 'TAG', 'GPU', 'QEMU', 'API', 'ABI']:
                paint_vars[col_name] = self.request.get_all(col_name)

            bq = bqclient.BigQueryClient(http)
            title, QUERY, SUM_QUERY, ADB_QUERY = get_query_clause(paint_vars)
            count, boot_values = bq2table(bq.Query(QUERY, BILLING_PROJECT_ID))
            #sum_count, sum_values = bq2table(bq.Query(SUM_QUERY, BILLING_PROJECT_ID))
            adb_count, adb_values = bq2table(bq.Query(ADB_QUERY, BILLING_PROJECT_ID))
            template_data = {'table_bootdata': boot_values,
                    'table_adbdata': adb_values,
                    'table_sumdata': 0,
                    'table_title': title,
                    'table_row_count': count,
                    'query_complete': 1,
                    'paint_vars': json.dumps(paint_vars),
                    'query': QUERY}
        template = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(render(template, template_data))

application = webapp2.WSGIApplication([
    ('/', MainPage),
], debug=True)

