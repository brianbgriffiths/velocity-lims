from django.urls import path, re_path
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpRequest, JsonResponse
from django.http import HttpResponse, HttpRequest, JsonResponse
import pylims, json, os
from pydantic import BaseModel, EmailStr, constr, ValidationError, validator
import psycopg
from psycopg import sql
from psycopg.rows import dict_row 
from psycopg.pq import Escaping
import importlib
import time

import bcrypt

def handlePost(request):
    if request.method == 'POST':
        try:
            json_data = json.loads(request.body)
            return 200
        except json.JSONDecodeError as e:
            return 400
    return 405

current_directory = os.path.dirname(os.path.abspath(__file__))
self = os.path.basename(current_directory)
scriptname = os.path.basename(__file__)

def begin_step(request):
    response_code = handlePost(request)
    if response_code==400:
        response_data = {'error': 'Invalid JSON data', 'message': str(e)}
        return JsonResponse(response_data, status=400)
    elif response_code==405:
        response_data = {'error': 'Invalid request method', 'message': 'Method not allowed'}
        return JsonResponse(response_data, status=405)
    json_data = json.loads(request.body)
    print('loaded json',json_data)

    response = {}

    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM velocity.step_config WHERE scid=%s",(json_data['step'],))
    response['config']=cursor.fetchone()
   
    cursor.execute("SELECT * FROM velocity.reserved_derivatives rd JOIN velocity.derivatives vd ON vd.did=rd.derivative JOIN velocity.samples vs ON vs.smid = vd.sample WHERE rd.step = %s and rd.operator=%s AND rd.status=1 ORDER BY rdid ASC;",(json_data['step'],request.session['userid']))
    samples = cursor.fetchall()
    response['samples'] = json.dumps(samples)
    response['reserved']=len(samples)

    if response['reserved']==0:
        response_data = {'error': 'nothing reserved', 'message': 'No reserved samples were found for this step.'}
        return JsonResponse(response_data)

    # cursor.execute("UPDATE velocity.reserved_derivatives rd SET status=2 WHERE rd.step = %s and rd.operator=%s AND rd.status=1 ORDER BY rdid ASC;",(json_data['step'],request.session['userid']))

    print('creating step', json_data['step'])
    cursor.execute("INSERT INTO velocity.steps (step_type, started) VALUES (%s, 0) RETURNING stepid",(json_data['step'],))
    print('fetching stepid')
    response['stepid']=cursor.fetchone()['stepid']

    cursor.execute("INSERT INTO velocity.containers (container_type, step) VALUES (%s, %s) RETURNING conid",(json_data['container'],response['stepid']))
    response['containerid']=cursor.fetchone()['conid']

    derivative_ids = []
    sample_keyed = {}
    for derivative in samples:
        sample_keyed[derivative['sample']]=derivative['did']
        derivative_ids.append(str(derivative['did']))

    

    # create the io map
    print('Creating Derivatives',derivative_ids)
    # Create the placeholders dynamically
    placeholders = ','.join(['%s'] * len(derivative_ids))

    # Update the query to include the placeholders
    query = f"""
        INSERT INTO velocity.derivatives (derivative_name, sample, derivative_step, container)
        SELECT derivative_name, sample, %s, %s
        FROM velocity.derivatives
        WHERE did IN ({placeholders})
        RETURNING did, sample;
    """

    # Combine the stepid and derivative_ids for substitution
    values = [response['stepid'],response['containerid']] + derivative_ids

    # Execute the query
    cursor.execute(query, values)
    returned_data = cursor.fetchall()
    new_sample_keyed = {}
    iomap=[]
    for new_derivative in returned_data:
        iomap.append([response['stepid'],sample_keyed[new_derivative['sample']],1,new_derivative['did'],1])

    cursor.executemany(
        """
        INSERT INTO velocity.step_io (step, input_derivative, input_number, output_derivative, output_number)
        VALUES (%s, %s, %s, %s, %s)
        """,
        iomap
    )

    conn.commit()
    conn.close()
    response['status']='success'
    return JsonResponse(response)

def load_step(request, step):
    # request.session['userid']
    print('loading step',step)
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    response = {}
    temp = {}

    cursor.execute("SELECT * FROM velocity.steps vs JOIN velocity.protocol_steps vps ON vps.sid=vs.step_type JOIN velocity.step_config vsc ON vsc.scid=vps.step_type JOIN velocity.protocols vp ON vp.pid=vps.protocol WHERE vs.stepid=%s;",(step,))
    response['config']=cursor.fetchone()
    print('config',response['config'])

    cursor.execute("SELECT sio.*, vdi.did as input_id, vdi.container as inputcontainer, vdo.did as output_id, vdo.container as outputcontainer, vs.* FROM velocity.step_io sio JOIN velocity.derivatives vdi ON vdi.did=sio.input_derivative JOIN velocity.derivatives vdo ON vdo.did=sio.output_derivative JOIN velocity.samples vs ON vs.smid=vdi.sample WHERE sio.step=%s",(step,))
    temp['io'] = cursor.fetchall()
    response['io'] = json.dumps(temp['io'])

    containerlist=[]
    response['inputcontainers']=[]
    response['outputcontainers']=[]

    for io in temp['io']:
        inputcontainer = io.get('inputcontainer',None)
        outputcontainer = io.get('outputcontainer',None)

        if inputcontainer and not inputcontainer in containerlist:
            containerlist.append(inputcontainer)
            response['inputcontainers'].append(inputcontainer)
        if outputcontainer and not outputcontainer in containerlist:
            containerlist.append(outputcontainer)
            response['outputcontainers'].append(outputcontainer)

    print('fetch containers:', containerlist)
    cursor.execute("SELECT * FROM velocity.containers vc JOIN velocity.container_config vcc ON vcc.cid = vc.container_type WHERE vc.conid = ANY(%s)",(containerlist,))
    response['containers']=json.dumps(cursor.fetchall())
    conn.close()

    return render(request, 'overhauls/placement.html', response)

urlpatterns=[
   path("steps/begin/", begin_step, name="begin_step"),
   path('step/<str:step>', load_step, name='load_step'),
    ]