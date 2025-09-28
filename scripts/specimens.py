from django.urls import path, re_path
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpRequest, JsonResponse
import pylims, json, os
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg import sql
from psycopg.pq import Escaping
from datetime import datetime
from django.urls import reverse

import bcrypt
from settings.views import context_init, login_required

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

@login_required
def display_specimens(request):
    context = context_init(request)
    response={}

    print(f'Loading last 20 requisitions for user {context["userid"]}')

    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM velocity.requisitions ORDER BY reqid DESC LIMIT 20;')
    temp_last_projects = cursor.fetchall()
    context['last_20'] = json.dumps(temp_last_projects)

    

    reqids = [x['reqid'] for x in temp_last_projects]
    print(reqids)

    cursor.execute('SELECT * FROM velocity.specimens WHERE req = ANY(%s)', (reqids,))
    specimens = cursor.fetchall()
    context['specimens']=json.dumps(specimens)

    print(f"Loaded {len(specimens)} specimens from {len(reqids)} requisitions")

    # Load samples created from these specimens and their assay information
    specimen_ids = [x['smid'] for x in specimens]
    cursor.execute('''
        SELECT * FROM velocity.specimen_assay WHERE specimen = ANY(%s)
    ''', (specimen_ids,))
    specimen_assays = cursor.fetchall()

    print(f"Loaded specimen assay data for {len(specimen_assays)} specimens")
    context['specimen_assays'] = {}
    for sa in specimen_assays:
        if not sa['specimen'] in context['specimen_assays']:
            context['specimen_assays'][sa['specimen']] = []
        context['specimen_assays'][sa['specimen']].append(sa)

    cursor.execute("SELECT * FROM velocity.assay JOIN velocity.assay_versions ON avid = active_version")
    temp_assays = cursor.fetchall()
    context['assays'] = parse_json_list(temp_assays)

    conn.close()
    return render(request, 'specimens.html', context)

def add_to_assay(request):
    response_code = handlePost(request)
    if response_code[0]==400:
        response_data = {'error': 'Invalid JSON data', 'message': str(response_code[1])}
        return JsonResponse(response_data, status=400)
    elif response_code[0]==405:
        response_data = {'error': 'Invalid request method', 'message': 'Method not allowed'}
        return JsonResponse(response_data, status=405)
    json_data = json.loads(request.body)
    response={}
    response['specimen_assay']=[]
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM velocity.assay JOIN velocity.assay_versions ON avid = active_version WHERE assayid = %s;",(json_data['assay'],))
    assay = cursor.fetchone()

    first_step = assay['assay_steps'][0]

    print('specimens requested:',json_data['samples'])

    cursor.execute(
        "SELECT qi.item_id FROM velocity.queued_items qi WHERE qi.queue_type=1 AND qi.item_type=1 AND qi.item_id = ANY(%s::BIGINT[])",
        (json_data['samples'],)
    )
    queued_specimens = cursor.fetchall()

    queued_specimens_list = [specimen['item_id'] for specimen in queued_specimens]
    print('queued specimens',queued_specimens_list)

    specimens_to_add = [item for item in json_data['samples'] if item not in queued_specimens_list]

    print('specimens to add:', specimens_to_add)


    if len(specimens_to_add) > 0:
        cursor.execute(
            "INSERT INTO velocity.queued_items (item_type, item_id, queue_type, queue_id) VALUES " +
            ", ".join(["(%s, %s, %s, %s)"] * len(specimens_to_add)),
            [val for specimen in specimens_to_add for val in ("1", specimen, "1", assay['active_version'])]
        )

        values = [
            (specimen, assay["assayid"], assay["active_version"], "1")
            for specimen in specimens_to_add
        ]

        # Build VALUES list safely
        values_sql = sql.SQL(",").join(
            sql.SQL("({})").format(
                sql.SQL(",").join(sql.Literal(v) for v in row)
            )
            for row in values
        )

        query = sql.SQL("""
            INSERT INTO velocity.specimen_assay (specimen, assay, version_added, status)
            VALUES {values}
            RETURNING said, specimen, assay, version_added, status
        """).format(values=values_sql)

        cursor.execute(query)
        response['specimen_assay'] = cursor.fetchall()
        conn.commit()
    else:
        print('NO SPECIMENS ADDED')

    
    response['specimens_added'] = len(specimens_to_add)
    response['specimens']=specimens_to_add
    response['assay'] = assay['assayid']
    response['status']='success'
    conn.close()
    return JsonResponse(response)
    