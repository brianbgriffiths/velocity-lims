from django.urls import path, re_path
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpRequest, JsonResponse
import pylims, json, os
import psycopg
from psycopg import sql
from psycopg.rows import dict_row 
from psycopg.pq import Escaping
from datetime import datetime
from django.urls import reverse

import bcrypt

def handlePost(request):
    if request.method == 'POST':
        try:
            json_data = json.loads(request.body)
            return [200,None]
        except json.JSONDecodeError as e:
            return [400,e]
    return [405,None]

def parse_json_dict(object):
    return json.dumps({
        key: (value.isoformat() if isinstance(value, datetime) else value)
        for key, value in object.items()
    })

def parse_json_list(list):
    return json.dumps([
        {key: (value.isoformat() if isinstance(value, datetime) else value) for key, value in row.items()}
        for row in list
    ])

current_directory = os.path.dirname(os.path.abspath(__file__))
self = os.path.basename(current_directory)
scriptname = os.path.basename(__file__)

def load_in_progress(request):
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute("SELECT steps.* FROM velocity.step_users vsu JOIN velocity.steps ON steps.stepid=vsu.step WHERE vsu.userid=%s AND steps.status=1 GROUP BY steps.stepid;",(request.session['userid'],))
    return cursor.fetchall()


def display_samples(request):
    response={}

    if not 'userid' in request.session:
        return redirect('/modules/login')

    print(f'Loading in-progress for {request.session['userid']}')
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM velocity.requisitions ORDER BY reqid DESC LIMIT 20;')
    temp_last_projects = cursor.fetchall()
    response['last_20'] = json.dumps(temp_last_projects)

    

    reqids = [x['reqid'] for x in temp_last_projects]
    print(reqids)

    cursor.execute('SELECT * FROM velocity.samples WHERE req = ANY(%s)', (reqids,))
    response['samples']=json.dumps(cursor.fetchall())

    cursor.execute("SELECT * FROM velocity.assay JOIN velocity.workflows ON wfid = active_workflow")
    temp_assays = cursor.fetchall()
    response['assays'] = parse_json_list(temp_assays)
    
    conn.close()
    return render(request, 'overhauls/samples.html', response)

def add_to_assay(request):
    response_code = handlePost(request)
    if response_code[0]==400:
        response_data = {'error': 'Invalid JSON data', 'message': str(response_code[1])}
        return JsonResponse(response_data, status=400)
    elif response_code[0]==405:
        response_data = {'error': 'Invalid request method', 'message': 'Method not allowed'}
        return JsonResponse(response_data, status=405)
    json_data = json.loads(request.body)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
   
    cursor.execute("SELECT * FROM velocity.assay JOIN velocity.workflows ON wfid = active_workflow WHERE assayid = %s;",(json_data['assay'],))
    assay = cursor.fetchone()

    first_step = assay['workflow_steps'][0]

    print('samples requested:',json_data['samples'])

    cursor.execute(
        "SELECT vd.sample FROM velocity.queued_derivatives qd JOIN velocity.derivatives vd ON vd.did=qd.derivative WHERE queue = %s AND vd.sample = ANY(%s::BIGINT[])",
        (first_step, json_data['samples'])
    )
    queued_samples = cursor.fetchall()

    queued_samples_list = [sample['sample'] for sample in queued_samples]
    print('queued samples',queued_samples_list)

    samples_to_add = [item for item in json_data['samples'] if item not in queued_samples_list]

    print('samples to add:', samples_to_add)


    if len(samples_to_add) > 0:
        cursor.execute(
            "INSERT INTO velocity.derivatives (sample, derivative_wf) VALUES " +
            ", ".join(["(%s, %s)"] * len(samples_to_add)) + 
            " RETURNING did;",
            [val for sample in samples_to_add for val in (sample, assay['active_workflow'])]
        )
        new_ids = [row['did'] for row in cursor.fetchall()]

        cursor.executemany(
            "INSERT INTO velocity.queued_derivatives (derivative, queue) VALUES (%s, %s)",
            [(new_id, first_step) for new_id in new_ids]
        )
        conn.commit()
    else:
        print('NO SAMPLES ADDED')

    response={}
    response['samples_added'] = len(samples_to_add)
    response['samples']=samples_to_add
    response['assay'] = assay['assayid']
    response['status']='success'
    conn.close()
    return JsonResponse(response)
    

urlpatterns=[
   path("samples/", display_samples, name="display_samples"),
   path("add_to_assay/", add_to_assay, name="add_to_assay"),
    ]