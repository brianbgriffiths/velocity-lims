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
from settings.views import login_required

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

    cursor.execute("SELECT vs.* FROM velocity.step_users vsu JOIN velocity.steps vs ON vs.stepid=vsu.step WHERE vsu.userid=%s AND vs.status=1 GROUP BY vs.stepid;",(request.session['userid'],))
    return cursor.fetchall()


def load_queues(request):
    response={}

    if not 'userid' in request.session:
        return False

    print(f'Loading in-progress for {request.session['userid']}')
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    
   
    cursor.execute("SELECT *, (select count(*) FROM velocity.queued_samples qd WHERE qd.queue=vs.sid) as samples FROM velocity.protocol_steps vs JOIN velocity.step_config sc ON sc.scid=vs.step_type JOIN velocity.protocols vp ON vp.pid = vs.protocol ORDER BY vs.protocol, vs.order_in_protocol;")
    response['queues'] = cursor.fetchall()    
    
    cursor.execute("SELECT va.assay_name, vsc.step_name, vsu.step FROM velocity.step_users vsu JOIN velocity.steps ON steps.stepid=vsu.step JOIN velocity.step_config vsc ON vsc.scid=steps.step_type JOIN LATERAL jsonb_array_elements(steps.workflow::jsonb) AS wf_id ON TRUE JOIN velocity.workflows vwf ON vwf.wfid = (wf_id)::int JOIN velocity.assay va ON va.assayid=vwf.assay WHERE vsu.userid=%s AND steps.status=1 GROUP BY vsu.step, vsc.step_name, va.assay_name",(request.session['userid'],))
    response['inprogress'] = cursor.fetchall()
    print(f'In Progress: {len(response['inprogress'])}')

    response['status']='success'
    conn.close()
    return response

def load_queue(params):
    response={}
    
    if not 'userid' in params:
        response['error']='no userid'
        response['status']='failed'
        return response
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
   
    cursor.execute("SELECT *, (select count(*) FROM velocity.queued_samples qd WHERE qd.queue=vs.sid) as samples FROM velocity.protocol_steps vs JOIN velocity.step_config sc ON sc.scid=vs.step_type JOIN velocity.protocols vp ON vp.pid = vs.protocol WHERE vs.sid=%s LIMIT 1;",(params['queue'],))
    response['queue'] = cursor.fetchone()

    # print('samples',response['queue']['samples'])

    # print('controls',response['queue']['controls'])

    cursor.execute("SELECT * FROM velocity.controls WHERE ctrlid = ANY(%s);",(response['queue']['controls'],))
    response['controls'] = json.dumps(cursor.fetchall())

    cursor.execute("SELECT * FROM velocity.queued_samples qd JOIN velocity.samples vd ON vd.sampleid=qd.sample JOIN velocity.specimens vs ON vs.smid = vd.requisition LEFT JOIN velocity.reserved_samples rd ON rd.step = qd.queue and rd.sample=qd.sample and rd.operator=%s and rd.status=1 WHERE qd.queue = %s ORDER BY qsid",(params['userid'],params['queue']))
    response['samples'] = json.dumps(cursor.fetchall())

    # print('sample list',response['samples'])

    
    response['status']='success'
    conn.close()
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

    cursor.execute("SELECT * FROM velocity.reserved_samples rd JOIN velocity.samples vd ON vd.sampleid=rd.sample JOIN velocity.specimens vs ON vs.smid = vd.requisition WHERE rd.step = %s and rd.operator=%s and rd.status=1 ORDER BY rsid ASC;",(params['reserved'],params['userid']))
    samples = cursor.fetchall()
    response['samples'] = json.dumps(samples)
    response['reserved']=len(samples)
    
    response['status']='success'
    conn.close()
    return response

@login_required
def display_queues(request):
    context=load_queues(request)
    context['inprogess']=load_in_progress(request)
    context['userid'] = request.session.get('userid', None)
    if len(context['inprogress'])>0:
        context['inprogress'] = parse_json_list(context['inprogress'])

    print('inprogress',context['inprogress'])
    return render(request, 'queues.html', context)

def display_queue(request,queue):
    options_to_send={}
    options_to_send['userid']=request.session['userid']
    options_to_send['queue']=queue
    context=load_queue(options_to_send)
    return render(request, 'queue.html', context)

def display_reserved(request,reserved):
    options_to_send={}
    options_to_send['userid']=request.session['userid']
    options_to_send['reserved']=reserved
    context=load_reserved(options_to_send)
    return render(request, 'reserved.html', context)

def reserve_sample(request):
    response_code = handlePost(request)
    if response_code[0]==400:
        response_data = {'error': 'Invalid JSON data', 'message': str(response_code[1])}
        return JsonResponse(response_data, status=400)
    elif response_code[0]==405:
        response_data = {'error': 'Invalid request method', 'message': 'Method not allowed'}
        return JsonResponse(response_data, status=405)
    json_data = json.loads(request.body)
    print('loaded json',json_data)

    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
   
    cursor.execute("INSERT INTO velocity.reserved_samples (sample, step, operator) VALUES (%s,%s,%s) ON CONFLICT (step, sample) DO NOTHING;",(json_data['sample'],json_data['step'],request.session['userid']))
    conn.commit()

    response={}
    response['status']='success'
    conn.close()
    return JsonResponse(response)

def reserve_samples(request):
    response_code = handlePost(request)
    if response_code[0]==400:
        response_data = {'error': 'Invalid JSON data', 'message': str(response_code[1])}
        return JsonResponse(response_data, status=400)
    elif response_code[0]==405:
        response_data = {'error': 'Invalid request method', 'message': 'Method not allowed'}
        return JsonResponse(response_data, status=405)
    json_data = json.loads(request.body)
    print('loaded json',json_data)

    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    print(json_data['samples'])
   
    cursor.executemany(
        "INSERT INTO velocity.reserved_samples (sample, step, operator) VALUES (%s, %s, %s) ON CONFLICT (step, sample) DO NOTHING;",
        [(sample, json_data['step'], request.session['userid']) for sample in json_data['samples']]
    )
    conn.commit()

    response={}
    response['status']='success'
    conn.close()
    return JsonResponse(response)

def remove_samples(request):
    response_code = handlePost(request)
    if response_code[0]==400:
        response_data = {'error': 'Invalid JSON data', 'message': str(response_code[1])}
        return JsonResponse(response_data, status=400)
    elif response_code[0]==405:
        response_data = {'error': 'Invalid request method', 'message': 'Method not allowed'}
        return JsonResponse(response_data, status=405)
    json_data = json.loads(request.body)
    print('loaded json',json_data)

    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM velocity.queued_samples WHERE queue = %s AND sample = ANY(%s);",
        (json_data['step'], json_data['samples'])
    )
    conn.commit()

    print(json_data['samples'])

    response={}
    response['status']='success'
    conn.close()
    return JsonResponse(response)

def release_sample(request):
    response_code = handlePost(request)
    if response_code[0]==400:
        response_data = {'error': 'Invalid JSON data', 'message': str(response_code[1])}
        return JsonResponse(response_data, status=400)
    elif response_code[0]==405:
        response_data = {'error': 'Invalid request method', 'message': 'Method not allowed'}
        return JsonResponse(response_data, status=405)
    json_data = json.loads(request.body)
    print('loaded json',json_data)

    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
   
    cursor.execute("DELETE FROM velocity.reserved_samples rd WHERE rd.sample = %s and rd.step=%s and rd.operator = %s and rd.status=1;",(json_data['sample'],json_data['step'],request.session['userid']))
    conn.commit()

    response={}
    response['status']='success'
    conn.close()
    return JsonResponse(response)

def release_all_samples(request):
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
   
    cursor.execute("DELETE FROM velocity.reserved_samples rd WHERE rd.step=%s and rd.operator = %s AND rd.status=1;",(json_data['step'],request.session['userid']))
    conn.commit()

    response={}
    response['status']='success'
    conn.close()
    return JsonResponse(response)

def add_control(request):
    response_code = handlePost(request)
    if response_code[0]==400:
        response_data = {'error': 'Invalid JSON data', 'message': str(response_code[1])}
        return JsonResponse(response_data, status=400)
    elif response_code[0]==405:
        response_data = {'error': 'Invalid request method', 'message': 'Method not allowed'}
        return JsonResponse(response_data, status=405)
    json_data = json.loads(request.body)

    response={}
    temp={}

    print('adding control',json_data['control'],type(json_data['control']),'to step',json_data['step'])
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute("SELECT *, (select count(*) FROM velocity.queued_samples qs WHERE qs.queue=vs.sid) as samples FROM velocity.protocol_steps vs JOIN velocity.step_config sc ON sc.scid=vs.step_type JOIN velocity.protocols vp ON vp.pid = vs.protocol WHERE vs.sid=%s LIMIT 1;",(json_data['step'],))
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
    
    cursor.execute("INSERT INTO velocity.specimens (req, specimen_name, control) VALUES (-1, %s, %s) RETURNING smid",(temp['control']['control_type'],temp['control']['ctrlid']))
    temp['sample_id'] = cursor.fetchone()['smid']

    cursor.execute("INSERT INTO velocity.samples (sample_name,requisition,creation_step) VALUES (%s, %s, -1) RETURNING sampleid",(temp['control']['control_type'],temp['sample_id']))
    temp['created_sample_id'] = cursor.fetchone()['sampleid']

    cursor.execute("INSERT INTO velocity.queued_samples (sample, queue) VALUES (%s, %s) RETURNING qsid",(temp['created_sample_id'], json_data['step']))
    temp['queued_sample'] = cursor.fetchone()['qsid']

    cursor.execute("INSERT INTO velocity.reserved_samples (sample, step, operator) VALUES (%s, %s, %s) RETURNING rsid",(temp['created_sample_id'], json_data['step'],request.session['userid']))
    conn.commit()

    cursor.execute("SELECT * FROM velocity.queued_samples qd JOIN velocity.samples vd ON vd.sampleid=qd.sample JOIN velocity.specimens vs ON vs.smid = vd.requisition LEFT JOIN velocity.reserved_samples rd ON rd.step = qd.queue and rd.sample=qd.sample and rd.operator=%s WHERE qd.qsid = %s",(request.session['userid'],temp['queued_sample']))
    response['samples'] = json.dumps(cursor.fetchall())

    response['status']='success'
    conn.close()
    return JsonResponse(response)

def add_all_controls(request):
    pass

def remove_controls(request):
    response_code = handlePost(request)
    if response_code[0]==400:
        response_data = {'error': 'Invalid JSON data', 'message': str(response_code[1])}
        return JsonResponse(response_data, status=400)
    elif response_code[0]==405:
        response_data = {'error': 'Invalid request method', 'message': 'Method not allowed'}
        return JsonResponse(response_data, status=405)
    json_data = json.loads(request.body)

    response={}
    temp={}
    
    print('removing control',json_data['queue_id'],'from',json_data['step'])

    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM velocity.queued_samples qd JOIN velocity.samples vd ON vd.sampleid=qd.sample JOIN velocity.specimens vs ON vs.smid=vd.requisition WHERE qd.qsid = %s;",(json_data['queue_id'],))
    temp['control'] = cursor.fetchone()

    if temp['control'] == None:
        response_data = {'error': 'no control', 'message': 'Queued Control not found'}
        return JsonResponse(response_data)
    
    print(f'DELETE FROM velocity.reserved_samples rd WHERE rd.sample = {temp['control']['sample']} and step={temp['control']['queue']} and operator={request.session['userid']}')
    cursor.execute("DELETE FROM velocity.reserved_samples rd WHERE rd.sample=%s and rd.step=%s and rd.operator=%s;",(temp['control']['sample'],temp['control']['queue'],request.session['userid']))
    conn.commit()

    cursor.execute("DELETE FROM velocity.queued_samples qd WHERE qd.qsid = %s;",(temp['control']['qsid'],))
    conn.commit()
    
    
    print('removing control',temp['control'])

    response['qsid']=temp['control']['qsid']

    response['status']='success'
    conn.close()
    return JsonResponse(response)


