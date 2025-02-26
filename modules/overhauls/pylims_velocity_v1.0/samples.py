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

    cursor.execute("SELECT * FROM velocity.assay")
    temp_assays = cursor.fetchall()
    response['assays'] = parse_json_list(temp_assays)
    
    conn.close()
    return render(request, 'overhauls/samples.html', response)
    

urlpatterns=[
   path("samples/", display_samples, name="display_samples"),
    ]