#!/usr/bin/env python
'''
Main file for dbsync / dbimport
'''

import json
import os
from flask import Flask, request
from google.cloud import tasks_v2

from gouv_fr.update import import_data_gouv_fr
from johns_hopkins_github.update import import_data_johns_hopkins_github
from ecdc_cases.update import update_data_ecdc_cases
from rki_cases.update import update_data_rki_cases


# This is the way it is documented
# pylint: disable=invalid-name
app = Flask(__name__)


PROJECT = os.environ['GOOGLE_CLOUD_PROJECT']
LOCATION = "europe-west3"
QUEUE = "data-import"


# This is an internally used interface
# which will change at any time.
# Don't use it!
@app.route('/v1/trigger/import_data/<source>')
def import_data_trigger(source):
    '''This triggers the import via a Cloud Task'''
    print("import_data_trigger called for [%s]" % source)

    environment = request.args.get("env", default="prod", type=str)
    ignore_errors = request.args.get("ignore-errors", default=True, type=bool)
    print("import_data_trigger environment [%s] ignore-errors [%s]"
          % (environment, ignore_errors))

    if environment not in ["prod", "test"]:
        print("Wrong paramter for environment [%s]" % environment)
        return "Wrong input parameter", 422

    # Data passed to the real funtion
    jdata = {
        'source': source,
        'environment': environment,
        'ignore-errors': ignore_errors
    }

    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(PROJECT, LOCATION, QUEUE)

    # Construct the request body.
    task = {
        'app_engine_http_request': {  # Specify the type of request.
            'http_method': 'POST',
            'relative_uri': '/v1/task/import_data',
            'body': json.dumps(jdata).encode()
        }
    }

    response = client.create_task(parent, task)

    print("Created task {}".format(response.name))
    print("import_data_trigger finished for [%s]" % source)
    return "import_data_trigger ok", 200


@app.route('/v1/task/import_data', methods=['POST', ])
def import_data():
    '''The real import function'''
    jdata = json.loads(request.get_data(as_text=True))
    print("import_data called with parameters [%s]" % jdata)

    source = jdata['source']
    # ToDo: this should be a module and loaded during runtime
    if source == 'johns_hopkins_github':
        import_data_johns_hopkins_github(
            jdata['environment'], jdata['ignore-errors'])
    elif source == 'ecdc_cases':
        update_data_ecdc_cases(
            jdata['environment'], jdata['ignore-errors'])
    elif source == 'gouv_fr':
        import_data_gouv_fr(
            jdata['environment'], jdata['ignore-errors'])
    elif source == 'rki_cases':
        update_data_rki_cases(
            jdata['environment'], jdata['ignore-errors'])
    else:
        print("*** ERROR: unknown source [%s]" % source)

    print("import_data finished for [%s]" % source)
    return "import_data ok", 200


@app.route('/')
def main():
    '''Test function'''
    return 'Hello, World!'


if __name__ == '__main__':
    main()