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

def load_queues(params):
    response={}
    
    if not 'userid' in params:
        response['error']='no userid'
        response['status']='failed'
        return response
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
   
    cursor.execute("SELECT *, (select count(*) FROM velocity.queued_derivatives qd WHERE qd.queue=vs.sid) as samples FROM velocity.protocol_steps vs JOIN velocity.step_config sc ON sc.scid=vs.step_type JOIN velocity.protocols vp ON vp.pid = vs.protocol ORDER BY vs.protocol, vs.order_in_protocol;")
    response['queues'] = cursor.fetchall()    
    
    response['status']='success'
    return response

def load_queue(params):
    response={}
    
    if not 'userid' in params:
        response['error']='no userid'
        response['status']='failed'
        return response
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
   
    cursor.execute("SELECT *, (select count(*) FROM velocity.queued_derivatives qd WHERE qd.queue=vs.sid) as samples FROM velocity.protocol_steps vs JOIN velocity.step_config sc ON sc.scid=vs.step_type JOIN velocity.protocols vp ON vp.pid = vs.protocol WHERE vs.sid=%s LIMIT 1;",(params['queue'],))
    response['queue'] = cursor.fetchone()

    print('controls',response['queue']['controls'])

    cursor.execute("SELECT * FROM velocity.controls WHERE ctrlid = ANY(%s);",(response['queue']['controls'],))
    response['controls'] = json.dumps(cursor.fetchall())

    cursor.execute("SELECT * FROM velocity.queued_derivatives qd JOIN velocity.derivatives vd ON vd.did=qd.derivative JOIN velocity.samples vs ON vs.smid = vd.sample LEFT JOIN velocity.reserved_derivatives rd ON rd.step = qd.queue and rd.derivative=qd.derivative and rd.operator=%s and rd.status=1 WHERE qd.queue = %s",(params['userid'],params['queue']))
    response['samples'] = json.dumps(cursor.fetchall())

    
    response['status']='success'
    return response

def load_reserved(params):
    response={}
    
    if not 'userid' in params:
        response['error']='no userid'
        response['status']='failed'
        return response
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
   
    cursor.execute("SELECT * FROM velocity.queues vq JOIN velocity.protocol_steps vs ON vs.sid=vq.qid JOIN velocity.step_config sc ON sc.scid=vs.step_type JOIN velocity.protocols vp ON vp.pid = vs.protocol WHERE vq.qid=%s LIMIT 1;",(params['reserved'],))
    response['queue'] = cursor.fetchone()

    print('controls',response['queue']['containers'])

    cursor.execute("SELECT * FROM velocity.container_config WHERE cid = ANY(%s);",(response['queue']['containers'],))
    response['containers'] = json.dumps(cursor.fetchall())

    cursor.execute("SELECT * FROM velocity.reserved_derivatives rd JOIN velocity.derivatives vd ON vd.did=rd.derivative JOIN velocity.samples vs ON vs.smid = vd.sample WHERE rd.step = %s and rd.operator=%s and rd.status=1 ORDER BY rdid ASC;",(params['reserved'],params['userid']))
    samples = cursor.fetchall()
    response['samples'] = json.dumps(samples)
    response['reserved']=len(samples)
    
    response['status']='success'
    return response

def display_queues(request):
    options_to_send={}
    options_to_send['userid']=request.session['userid']
    context=load_queues(options_to_send)
    return render(request, 'overhauls/queues.html', context)

def display_queue(request,queue):
    options_to_send={}
    options_to_send['userid']=request.session['userid']
    options_to_send['queue']=queue
    context=load_queue(options_to_send)
    return render(request, 'overhauls/queue.html', context)

def display_reserved(request,reserved):
    options_to_send={}
    options_to_send['userid']=request.session['userid']
    options_to_send['reserved']=reserved
    context=load_reserved(options_to_send)
    return render(request, 'overhauls/reserved.html', context)

def reserve_sample(request):
    response_code = handlePost(request)
    if response_code==400:
        response_data = {'error': 'Invalid JSON data', 'message': str(e)}
        return JsonResponse(response_data, status=400)
    elif response_code==405:
        response_data = {'error': 'Invalid request method', 'message': 'Method not allowed'}
        return JsonResponse(response_data, status=405)
    json_data = json.loads(request.body)
    print('loaded json',json_data)

    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
   
    cursor.execute("INSERT INTO velocity.reserved_derivatives (derivative, step, operator) VALUES (%s,%s,%s) ON CONFLICT (step, derivative) DO NOTHING;",(json_data['sample'],json_data['step'],request.session['userid']))
    conn.commit()

    response={}
    response['status']='success'
    return JsonResponse(response)

def release_sample(request):
    response_code = handlePost(request)
    if response_code==400:
        response_data = {'error': 'Invalid JSON data', 'message': str(e)}
        return JsonResponse(response_data, status=400)
    elif response_code==405:
        response_data = {'error': 'Invalid request method', 'message': 'Method not allowed'}
        return JsonResponse(response_data, status=405)
    json_data = json.loads(request.body)
    print('loaded json',json_data)

    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
   
    cursor.execute("DELETE FROM velocity.reserved_derivatives rd WHERE rd.derivative = %s and rd.step=%s and rd.operator = %s and rd.status=1;",(json_data['sample'],json_data['step'],request.session['userid']))
    conn.commit()

    response={}
    response['status']='success'
    return JsonResponse(response)

def release_all_samples(request):
    response_code = handlePost(request)
    if response_code==400:
        response_data = {'error': 'Invalid JSON data', 'message': str(e)}
        return JsonResponse(response_data, status=400)
    elif response_code==405:
        response_data = {'error': 'Invalid request method', 'message': 'Method not allowed'}
        return JsonResponse(response_data, status=405)
    json_data = json.loads(request.body)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
   
    cursor.execute("DELETE FROM velocity.reserved_derivatives rd WHERE rd.step=%s and rd.operator = %s AND rd.status=1;",(json_data['step'],request.session['userid']))
    conn.commit()

    response={}
    response['status']='success'
    return JsonResponse(response)

def add_control(request):
    response_code = handlePost(request)
    if response_code==400:
        response_data = {'error': 'Invalid JSON data', 'message': str(e)}
        return JsonResponse(response_data, status=400)
    elif response_code==405:
        response_data = {'error': 'Invalid request method', 'message': 'Method not allowed'}
        return JsonResponse(response_data, status=405)
    json_data = json.loads(request.body)

    response={}
    temp={}

    print('adding control',json_data['control'],type(json_data['control']),'to step',json_data['step'])
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute("SELECT *, (select count(*) FROM velocity.queued_derivatives qd WHERE qd.queue=vs.sid) as samples FROM velocity.protocol_steps vs JOIN velocity.step_config sc ON sc.scid=vs.step_type JOIN velocity.protocols vp ON vp.pid = vs.protocol WHERE vs.sid=%s LIMIT 1;",(json_data['step'],))
    temp['queue'] = cursor.fetchone()

    print('step controls',temp['queue']['controls'])

    if len(temp['queue']['controls'])==0:
        temp['error']="No controls found for this step"
        return JsonResponse(temp)
    
    print('controls',temp['queue']['controls'])
    
    if not int(json_data['control']) in temp['queue']['controls']:
        print("Control is not enabled for this step")
        response['error']="Control is not enabled for this step"
        return JsonResponse(response)
    
    cursor.execute("SELECT * FROM velocity.controls WHERE ctrlid = %s;",(json_data['control'],))
    temp['control'] = cursor.fetchone()
    print('control',temp['control'])
    
    cursor.execute("INSERT INTO velocity.samples (project, sample_name, control) VALUES (-1, %s, %s) RETURNING smid",(temp['control']['control_type'],temp['control']['ctrlid']))
    temp['sample_id'] = cursor.fetchone()['smid']

    cursor.execute("INSERT INTO velocity.derivatives (sample,derivative_step) VALUES (%s, -1) RETURNING did",(temp['sample_id'],))
    temp['did'] = cursor.fetchone()['did']

    cursor.execute("INSERT INTO velocity.queued_derivatives (derivative, queue) VALUES (%s, %s) RETURNING qdid",(temp['did'], json_data['step']))
    temp['queued_derivative'] = cursor.fetchone()['qdid']

    cursor.execute("INSERT INTO velocity.reserved_derivatives (derivative, step, operator) VALUES (%s, %s, %s) RETURNING rdid",(temp['did'], json_data['step'],request.session['userid']))
    conn.commit()

    cursor.execute("SELECT * FROM velocity.queued_derivatives qd JOIN velocity.derivatives vd ON vd.did=qd.derivative JOIN velocity.samples vs ON vs.smid = vd.sample LEFT JOIN velocity.reserved_derivatives rd ON rd.step = qd.queue and rd.derivative=qd.derivative and rd.operator=%s WHERE qd.qdid = %s",(request.session['userid'],temp['queued_derivative']))
    response['samples'] = json.dumps(cursor.fetchall())

    response['status']='success'

    return JsonResponse(response)

def add_all_controls(request):
    pass

def remove_controls(request):
    response_code = handlePost(request)
    if response_code==400:
        response_data = {'error': 'Invalid JSON data', 'message': str(e)}
        return JsonResponse(response_data, status=400)
    elif response_code==405:
        response_data = {'error': 'Invalid request method', 'message': 'Method not allowed'}
        return JsonResponse(response_data, status=405)
    json_data = json.loads(request.body)

    response={}
    temp={}
    
    print('removing control',json_data['queue_id'],'from',json_data['step'])

    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM velocity.queued_derivatives qd JOIN velocity.derivatives vd ON vd.did=qd.derivative JOIN velocity.samples vs ON vs.smid=vd.sample WHERE qd.qdid = %s;",(json_data['queue_id'],))
    temp['control'] = cursor.fetchone()

    if temp['control'] == None:
        response_data = {'error': 'no control', 'message': 'Queued Control not found'}
        return JsonResponse(response_data)
    
    print(f'DELETE FROM velocity.reserved_derivatives rd WHERE rd.derivative = {temp['control']['derivative']} and step={temp['control']['queue']} and operator={request.session['userid']}')
    cursor.execute("DELETE FROM velocity.reserved_derivatives rd WHERE rd.derivative=%s and rd.step=%s and rd.operator=%s;",(temp['control']['derivative'],temp['control']['queue'],request.session['userid']))
    conn.commit()

    cursor.execute("DELETE FROM velocity.queued_derivatives qd WHERE qd.qdid = %s;",(temp['control']['qdid'],))
    conn.commit()
    
    
    print('removing control',temp['control'])

    response['qdid']=temp['control']['qdid']

    response['status']='success'
    return JsonResponse(response)


urlpatterns=[
   path("queues/", display_queues, name="display_queues"),
   path('queue/<str:queue>', display_queue, name='display_queue'),
   path('reserved/<str:reserved>', display_reserved, name='display_reserved'),
   path('reserve/',reserve_sample, name='reserve_sample'),
   path('release/',release_sample, name='release_sample'),
   path('releaseall/',release_all_samples, name='release_all_samples'),
   path('addcontrol/',add_control, name='add_control'),
   path('addallcontrols/',add_all_controls, name='add_all_controls'),
   path('controls/remove/',remove_controls, name='remove_controls'),
    ]