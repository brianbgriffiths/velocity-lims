from django.urls import path, re_path
from django.http import HttpResponse, HttpRequest, JsonResponse
import pylims, json, os
from pydantic import BaseModel, EmailStr, constr, ValidationError, validator
import psycopg
from psycopg.rows import dict_row
import bcrypt
import base64
from PIL import Image
from io import BytesIO
import psycopg
from psycopg import sql
from psycopg.rows import dict_row 
from psycopg.pq import Escaping

current_directory = os.path.dirname(os.path.abspath(__file__))
self = os.path.basename(current_directory)

def admin_list_automations(request):
    accepted_permissions=['automations_configure']
    response={}
    
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)

    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM automation_step ORDER BY name ASC")
    
    results = cursor.fetchall()
    print('step count:',len(results))
    response['data']=results
    cursor.close()
    conn.close()

    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)

def create_new_step(request):
    accepted_permissions=['automations_configure']
    response={}
    
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    
    data = json.loads(request.body)

    if len(data['new_step_name'])<3:
        response['error']='New Step name not long enough'
        return JsonResponse(response)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM automation_step WHERE name=%s LIMIT 1;",(data['new_step_name'],))
    
    result = cursor.fetchall()
    print('New Step count:',len(result))

    if len(result)>0:
        response['error']='Step with this name already exists'
        return JsonResponse(response)

    

    cursor.execute("INSERT INTO automation_step (name,status,version) VALUES (%s, '1','0.0.1') RETURNING asid;",(data['new_step_name'],))
    response['new_id'] = cursor.fetchone()['asid']
    response['new_name'] = data['new_step_name']
    conn.commit()
    cursor.close()
    conn.close()

    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)


urlpatterns=[
    path('admin_list_automations/', admin_list_automations, name="admin_list_automations"),
    path('create_new_step/', create_new_step, name="create_new_step"),
    
    ]
    
