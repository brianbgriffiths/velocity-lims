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
import traceback
import time

import sys
from settings import settings
sys.path.append(os.path.join(settings.BASE_DIR, "custom_scripts"))

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

def run_script(request):
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

    cursor.execute("SELECT * FROM velocity.script_config WHERE scid=%s LIMIT 1;",(json_data['script'],))
    script_config = cursor.fetchone()

    cursor.execute("INSERT INTO velocity.script_runs (script, step, status) VALUES (%s, %s, %s) RETURNING srid;", (script_config['scid'],json_data['step'],1))
    script_run_id = cursor.fetchone()
    print('script runid',script_run_id['srid'])

    #status
    #0 = queued
    #1 = running
    #2 = success
    #3 = error
    #4 = stall

    try:
        script_module = importlib.import_module(f'{script_config["script_file"]}')
        importlib.reload(script_module)
        script = getattr(script_module, "Script")
        # Create an instance and run the method
        instance = script(step=json_data['step'])
        response['run_status'], response['script_message'], response['script_updates'] = instance.run()
        cursor.execute("UPDATE velocity.script_runs SET status=%s, message=%s WHERE srid = %s;",(response['run_status'],response['script_message'],script_run_id['srid']))
    except Exception as e:
        tb = traceback.format_exc()
        response['status']='error'
        response['run_status']=3
        # response['script_message']=f'script error: {e} <pre>{tb}</pre>'
        response['script_message']=f'script error: {e}'
        response['script_updates']=None
        cursor.execute("UPDATE velocity.script_runs SET status=3, message=%s WHERE srid = %s;",(f'Error: {e}', script_run_id['srid']))
        conn.commit()
        conn.close()
        return JsonResponse(response)
    conn.commit()
    conn.close()
    response['status']='success'
    return JsonResponse(response)
