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
from datetime import datetime

import bcrypt

def handlePost(request):
    if request.method == 'POST':
        try:
            json_data = json.loads(request.body)
            return 200
        except json.JSONDecodeError as e:
            return 400
    return 405

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
    unique_wfids = list({row["derivative_wf"] for row in samples if row["derivative_wf"] is not None and row["derivative_wf"] != "null"})
    print('Derivative workflows:',unique_wfids)

    if response['reserved']==0:
        response_data = {'error': 'nothing reserved', 'message': 'No reserved samples were found for this step.'}
        return JsonResponse(response_data)

    # cursor.execute("UPDATE velocity.reserved_derivatives rd SET status=2 WHERE rd.step = %s and rd.operator=%s AND rd.status=1 ORDER BY rdid ASC;",(json_data['step'],request.session['userid']))


    print('creating step', json_data['step'])
    cursor.execute("INSERT INTO velocity.steps (step_type, started, on_page, workflow) VALUES (%s, %s, %s, %s) RETURNING stepid",(json_data['step'], datetime.now(), response['config']['pages'][0],json.dumps(unique_wfids)))
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
        INSERT INTO velocity.derivatives (derivative_name, sample, derivative_step, container, derivative_wf)
        SELECT derivative_name, sample, %s, %s, 1
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

    cursor.execute("INSERT INTO velocity.step_users (step, userid, action) VALUES (%s, %s, %s);",(response['stepid'], request.session['userid'],1))

    conn.commit()
    conn.close()
    response['status']='success'
    return JsonResponse(response)

def load_step(request, step, page=None):
    # request.session['userid']
    print('loading step',step,page)
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    response = {}
    temp = {}

    cursor.execute("""SELECT vs.*, vps.*, vsc.*, vp.*, vpc.* FROM velocity.steps vs JOIN velocity.page_config vpc ON vpc.pcid = vs.on_page JOIN velocity.protocol_steps vps ON vps.sid=vs.step_type JOIN velocity.step_config vsc ON vsc.scid=vps.step_type JOIN velocity.protocols vp ON vp.pid=vps.protocol WHERE vs.stepid=%s;""",(step,))
    step_config = cursor.fetchone()
    response['config'] = parse_json_dict(step_config) 
    # print('config',response['config'])

    cursor.execute("SELECT * FROM velocity.page_config;")
    temp_pages = cursor.fetchall()
    response['pages'] = json.dumps({page['pcid']: page for page in temp_pages})
    page_index = {page["page"]: str(page["pcid"]) for page in temp_pages}

    requested_page = step_config['on_page']
    if page:
        requested_page = page_index[page]


    cursor.execute("SELECT * FROM velocity.script_config WHERE scid = ANY(%s) AND run_on=%s;", (step_config['step_scripts'], requested_page))
    response['scripts'] = cursor.fetchall()
    if len(response['scripts']) > 0:
        response['scripts'] = parse_json_list(response['scripts'])
    

    cursor.execute("SELECT * FROM velocity.script_runs WHERE step=%s ORDER BY srid DESC;",(step,))
    response['script_runs'] = cursor.fetchall()
    if len(response['script_runs']) > 0:
        response['script_runs'] = parse_json_list(response['script_runs'])

    cursor.execute("SELECT sio.*, vwf.wfid, vwf.workflow_steps as output_steps, vdi.did as input_id, vdi.container as inputcontainer, vdo.did as output_id, vdo.container as outputcontainer, vdo.placement_string as output_well, vdo.placement_index as output_placement_index, vs.* FROM velocity.step_io sio JOIN velocity.derivatives vdi ON vdi.did=sio.input_derivative JOIN velocity.derivatives vdo ON vdo.did=sio.output_derivative JOIN velocity.samples vs ON vs.smid=vdi.sample JOIN velocity.workflows vwf ON vwf.wfid=vdo.derivative_wf WHERE sio.step=%s",(step,))
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

    cursor.execute("SELECT * FROM velocity.containers vc JOIN velocity.container_config vcc ON vcc.cid = vc.container_type WHERE vc.conid = ANY(%s)",(containerlist,))
    response['containers']=json.dumps(cursor.fetchall())
    
    print('load step data',step_config['stepid'],step_config['step_type'])
    cursor.execute("SELECT * FROM velocity.step_data_config sdc JOIN velocity.step_data_types sdt ON sdt.sdtid=sdc.value_type LEFT JOIN velocity.step_data vsd ON vsd.step=%s AND vsd.data_config = sdc.sdcid WHERE sdc.step_type=%s;",(step_config['stepid'],step_config['step_type']))
    temp['step_data']=cursor.fetchall()
    response['step_data'] = json.dumps(temp['step_data'])

    #get derivative data
    cursor.execute("SELECT * FROM velocity.derivative_data_config ddc WHERE ddc.ddcid=ANY(%s);",(step_config['derivative_data'],))
    temp['data_config'] = cursor.fetchall()
    response['data_config'] = json.dumps(temp['data_config'])


    get_data_config=[]
    gen_system_data=[]
    for data_type in temp['data_config']:
        if data_type['value_type']==1:
            gen_system_data.append(data_type['ddcid'])
            continue
        get_data_config.append(data_type['ddcid'])

    derivative_pairs = []
    output_data = {}
    for io in temp['io']:
        output_data[io['output_id']]={}
        output = output_data[io['output_id']]
        
        for config_id in gen_system_data:
            if config_id==1: # Sample Name
                output[config_id]=io['sample_name']
                continue
            elif config_id==2:
                output[config_id]=io['output_well']
                continue
            elif config_id==3:
                output[config_id]='Routing'
            else:
                output[config_id]='Unconfigured'
            
    for config_id in get_data_config:
        for output in temp['io']:
            derivative_pairs.append((output['output_id'],config_id))
    # print('derivative pairs:',derivative_pairs)
    cursor.execute("""
    CREATE TEMP TABLE temp_ids (
        derivative BIGINT,
        data_config BIGINT
    );
    """)

    # Insert derivative pairs into the temporary table
    cursor.executemany("""
    INSERT INTO temp_ids (derivative, data_config) VALUES (%s, %s);
    """, derivative_pairs)

    # Join with the main table to fetch all matching rows
    cursor.execute("""
    SELECT t.*
    FROM velocity.derivative_data t
    JOIN temp_ids tmp
    ON t.derivative = tmp.derivative AND t.data_config = tmp.data_config;
    """)

    # Fetch and process the results
    results = cursor.fetchall()

    # print('results',results)

    for data in results:
        # print(data)
        output_data[data['derivative']][data['data_config']]=data['value']

    response['output_data']=json.dumps(output_data)

    # for now i'm just going to dump all the step data. In the future, optomize only grab relevant step data.
    cursor.execute('SELECT scid, step_name FROM velocity.step_config')
    temp_step_names = cursor.fetchall()
    response['step_names']={}
    for tsd in temp_step_names:
        response['step_names'][tsd['scid']]=tsd['step_name']

    cursor.execute('SELECT assayid, assay_name FROM velocity.assay')
    temp_assay_names = cursor.fetchall()
    response['assay_names']={}
    for tan in temp_assay_names:
        response['assay_names'][tan['assayid']]=tan['assay_name']

    
    conn.close()
    response['loaded_page']=step_config['on_page']
    if page:
        response['loaded_page']=page_index[page]
        if step_config['status']==2:
            return render(request, f'overhauls/{page}-complete.html', response)
        return render(request, f'overhauls/{page}.html', response)
    return render(request, f'overhauls/{step_config['page']}.html', response)

def save_step(request):
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

    response = {}
    temp = {}

    step = json_data['step']
    print('saving step',step)

    cursor.executemany(
            """
            INSERT INTO velocity.step_data (step, data_config, value)
            VALUES (%s, %s, %s)
            ON CONFLICT (step, data_config)
            DO UPDATE SET value = EXCLUDED.value
            """,
            json_data['details']
        )
    
    print('outputs',json_data['outputs'])

    cursor.executemany(
            """
            INSERT INTO velocity.derivative_data (derivative, data_config, value)
            VALUES (%s, %s, %s)
            ON CONFLICT (derivative, data_config)
            DO UPDATE SET value = EXCLUDED.value
            """,
            json_data['outputs']
        )
    
    cursor.execute("INSERT INTO velocity.step_users (step, userid, action) VALUES (%s, %s, %s);",(step,request.session['userid'],2))
    
    conn.commit()
    conn.close()
    response['status']='success'
    return JsonResponse(response)



def next_step(request):
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

    response = {}
    temp = {}

    cursor.execute("SELECT * FROM velocity.page_config;")
    temp_pages = cursor.fetchall()
    response['pages'] = json.dumps({page['pcid']: page for page in temp_pages})
    page_index = {page["page"]: str(page["pcid"]) for page in temp_pages}

    step = json_data['step']
    print('preparing for next step',step)

    cursor.execute("SELECT vs.*, vps.*, vsc.*, vp.*, vpc.* FROM velocity.steps vs JOIN velocity.page_config vpc ON vpc.pcid = vs.on_page JOIN velocity.protocol_steps vps ON vps.sid=vs.step_type JOIN velocity.step_config vsc ON vsc.scid=vps.step_type JOIN velocity.protocols vp ON vp.pid=vps.protocol WHERE vs.stepid=%s;",(step,))
    config=cursor.fetchone()

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

    
    print('pages',config['pages'])
    
    if 'page' in json_data:
        print('requested from page',json_data['page'],page_index[json_data['page']])
        current_page_index = config['pages'].index(int(page_index[json_data['page']]))
        config['page']=json_data['page']
    else:
        print('on page',config['page'])
        current_page_index = config['pages'].index(config['on_page'])
    print('current page index',current_page_index)

    if config['page']=='placement':
        print('Checking placements')
        print('fetch containers:', containerlist)
        cursor.execute("SELECT * FROM velocity.containers vc JOIN velocity.container_config vcc ON vcc.cid = vc.container_type WHERE vc.conid = ANY(%s)",(containerlist,))
        containers_db = cursor.fetchall()

        container_dict = {}
        for row in containers_db:
            container_dict[str(row['conid'])]=row

        print('container_dict',container_dict)
        rownames=['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P']
        containers={}
        placements={}
        for key in json_data['placements']:
            container = str(json_data['placements'][key]['container'])
            index = int(json_data['placements'][key]['well'])
            sample = json_data['placements'][key].get('derivative',None)
            if not container in containers:
                rows = int(container_dict[container]['rows'])
                columns = int(container_dict[container]['columns'])
                placements[container] = {}
                containers[container] = [None] * (rows * columns)
                def index_to_grid(index):
                    row_index = index % rows
                    col_index = index // rows
                    return f'{rownames[row_index]}:{col_index+1}'
                
            containers[container][index]=sample
            placements[container][sample]=[index,index_to_grid(index)]

        print('placements',placements)

        for key in containers:
            cursor.execute("UPDATE velocity.containers SET placements=%s WHERE conid=%s;",(json.dumps(containers[key]),key))
            updates = [(values[0], values[1], did) for did, values in placements[key].items()]
            cursor.executemany(
            """
            UPDATE velocity.derivatives 
            SET placement_index = %s, placement_string = %s 
            WHERE did = %s;
            """,
            updates
        )
    elif config['page']=='details':
        #make sure all details are filled out. 
        #just going to assume they are for now :)
        pass
    elif config['page']=='routing':
        print('exit routing')
    elif config['page']=='confirmation':
        print('completing step')
        cursor.execute("UPDATE velocity.steps SET status=2 WHERE stepid=%s;",(config['stepid'],))
    else:
        print('this page is configured yet. we dont know what to do')
        response['status']='error'
        response['error']='Cant find next page key in script'
        conn.close()
        return JsonResponse(response)

        
        

    if len(config['pages'])>current_page_index+1:
        next_page = config['pages'][current_page_index+1]
        print('next page',next_page)
        cursor.execute("UPDATE velocity.steps SET on_page=%s WHERE stepid=%s;",(next_page,config['stepid']))
    
    conn.commit()
    conn.close()
    response['status']='success'
    return JsonResponse(response)

def save_placements(request):
    response_code = handlePost(request)
    if response_code==400:
        response_data = {'error': 'Invalid JSON data', 'message': str(e)}
        return JsonResponse(response_data, status=400)
    elif response_code==405:
        response_data = {'error': 'Invalid request method', 'message': 'Method not allowed'}
        return JsonResponse(response_data, status=405)
    json_data = json.loads(request.body)
    print('loaded json',json_data)

    step = json_data['step']

    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    response = {}
    temp = {}
    print('Checking placements')
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
    containers_db = cursor.fetchall()

    container_dict = {}
    for row in containers_db:
        container_dict[str(row['conid'])]=row

    print('container_dict',container_dict)

    rownames=['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P']
    containers={}
    placements={}
    for key in json_data['placements']:
        container = str(json_data['placements'][key]['container'])
        index = int(json_data['placements'][key]['well'])
        sample = json_data['placements'][key].get('derivative',None)
        if not container in containers:
            rows = int(container_dict[container]['rows'])
            columns = int(container_dict[container]['columns'])
            placements[container] = {}
            containers[container] = [None] * (rows * columns)
            def index_to_grid(index):
                row_index = index % rows
                col_index = index // rows
                return f'{rownames[row_index]}:{col_index+1}'
            
        containers[container][index]=sample
        placements[container][sample]=[index,index_to_grid(index)]

    print('placements',placements)

    for key in containers:
        cursor.execute("UPDATE velocity.containers SET placements=%s WHERE conid=%s;",(json.dumps(containers[key]),key))
        updates = [(values[0], values[1], did) for did, values in placements[key].items()]
        cursor.executemany(
        """
        UPDATE velocity.derivatives 
        SET placement_index = %s, placement_string = %s 
        WHERE did = %s;
        """,
        updates
    )
        
    cursor.execute("INSERT INTO velocity.step_users (step, userid, action) VALUES (%s, %s, %s);",(step, request.session['userid'],2))
        
    
    conn.commit()
    conn.close()
    response['status']='success'
    return JsonResponse(response)


urlpatterns=[
   path("steps/begin/", begin_step, name="begin_step"),
   path('step/<str:step>', load_step, name='load_step'),
   path('step/<str:step>/<str:page>', load_step, name='load_step'),
   path('step/nextstep/', next_step, name='next_step'),
   path('step/save/', save_step, name='save_step'),
   path('step/saveplacements/', save_placements, name='save_placements'),
    ]