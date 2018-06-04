#!/usr/bin/python
import model
import os
import json
import web
#Root path
base_path = os.path.dirname(os.path.abspath(__file__))

urls = (
    '', 'api',
    '(.+)/status/', 'status',
    '(.+)/summary/', 'summary',
    '(.+)/targets/', 'targets',
    '(.+)/targets/(.+)/', 'offtargets',
)

opal_client = model.OpalAdapter()

class api:
    def GET(self):
         return 'GT-Scan API. See main page at http://www.gt-scan.csiro.au'

class targets:
    def GET(self, job_id):
        web.header('Content-Type', 'application/json')
        db_path = os.path.join(base_path, 'static', 'results', job_id, 'crispr.db')
        return model.get_targets(db_path)

class offtargets:
    def GET(self, job_id, target_id):
        web.header('Content-Type', 'application/json')
        db_path = os.path.join(base_path, 'static', 'results', job_id, 'crispr.db')
        return model.get_offtargets(target_id, db_path)

class status:
    def GET(self, job_id):
        web.header('Content-Type', 'application/json')
        try:
            status_code = opal_client.getStatusCode(job_id)
            status = model.statii[status_code]
        except:
            return json.dumps({'data':{'color': 'red', 'message': 'Invalid job Id', 'statusCode': 0}}, indent=2)
        return json.dumps({'data':{'color': status[1], 'message': status[0], 'statusCode': status_code}}, indent=2)

class summary:
    def GET(self, job_id):
        web.header('Content-Type', 'application/json')
        db_path = os.path.join(base_path, 'static', 'results', job_id, 'crispr.db')
        return model.get_summary(db_path)

app_api = web.application(urls, locals())
