import configparser
import json
import os
import web
from opalpy import OpalClient
import sqlite3 as db

#Root path
base_path = os.path.dirname(os.path.abspath(__file__))

statii = {1:['Awaiting execution', ''],
          2:['Execution in progress', ''],
          4:['Error', 'red'],
          8:['Complete', 'green'],
          128:['Finishing', 'green']}

#Read the config.ini file to 'config'
config = configparser.ConfigParser()
config.optionxform=str
config.read_file(open(os.path.join(base_path, 'config.ini')))

opalURL = config.get('important','opal_app_url')

class OpalAdapter(object):
    def __init__(self):
        self.client = OpalClient.OpalService(opalURL)

    def getStatusCode(self, job_id):
        return OpalClient.JobStatus(self.client, job_id).getStatus()

    def launchJob(self, args, files):
        return self.client.launchJobNB( args, files )


def get_targets(path):
    try:
        con = db.connect(path)
        cur = con.cursor()
        cur.execute('SELECT * FROM targets')
        rows = cur.fetchall()
    except:
        rows = []
    return json.dumps({'data': rows})


def get_offtargets(target, path):
    try:
        con = db.connect(path)
        cur = con.cursor()
        cur.execute('SELECT * FROM "{0}"'.format(target))
        rows = cur.fetchall()
    except:
        rows = []
    return json.dumps({'data': rows})


def get_summary(path):
    try:
        row = get_summary_raw(path)
    except:
        row = ('','','','','','','','','')
    job_info = dict(zip(['name','rule','filter','mmlimit','genome','header','region','length', 'time'], row))
    return json.dumps({'data': job_info}, indent=2)


def get_summary_raw(path):
    con = db.connect(path)
    cur = con.cursor()
    cur.execute('SELECT * FROM info LIMIT 1')
    return cur.fetchall()[0]

