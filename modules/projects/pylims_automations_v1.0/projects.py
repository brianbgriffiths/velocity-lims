from django.urls import path, re_path
from django.http import HttpResponse, HttpRequest, JsonResponse
import pylims, json, os
from pydantic import BaseModel, EmailStr, constr, ValidationError, validator
import psycopg
from psycopg import sql
from psycopg.rows import dict_row 
from psycopg.pq import Escaping
import importlib
import bcrypt

current_directory = os.path.dirname(os.path.abspath(__file__))
self = os.path.basename(current_directory)
scriptname = os.path.basename(__file__)

def load_projects(params):
    response={}
    print('project automations')
    if not 'userid' in params:
        response['error']='no userid'
        response['status']='failed'
        return response
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    
    
    
    if 'query' in params and 'id' in params['query']:
        cursor.execute("SELECT * FROM projects WHERE pid=%s LIMIT 1", (int(params['query']['id']),))
        temp_project = cursor.fetchone()
        if temp_project==[]:
            response['error']='Project not found'
            response['status']='failed'
            return response
        response['projects']=[temp_project]  
        cursor.close()
        conn.close()
        response['status']='success'
        return response

    response['project_types']=['Production','Development','Validation','Test']    
    
    cursor.execute("SELECT * FROM projects ORDER BY pid DESC limit 100;")
    temp_projects = cursor.fetchall()
    if temp_projects == []:
        response['error']='No projects found'
        response['status']='failed'
        return response       
    
    
    project_ids = []
    response['projects']={}
    for project in temp_projects:
        project_ids.append(project["pid"])
        project['sample_count']=0
        project['samples']=[]
        response['projects'][project["pid"]]=project

    # print(pylims.term(),'PROJECT IDS',project_ids)
    settings=json.loads(pylims.get_setup_options())
    mods = json.loads(pylims.build_module_dict())

    module_to_import = importlib.import_module(mods['automations'][settings['setup']['automations']]['scripts'][0])
    function_to_call = getattr(module_to_import, 'load_automations')

    response['automations']=function_to_call({})

    module_to_import = importlib.import_module(mods['containers'][settings['setup']['containers']]['scripts'][0])
    function_to_call2 = getattr(module_to_import, 'load_containers')

    response['containers']=function_to_call2(params)

    module_to_import = importlib.import_module(mods['samples'][settings['setup']['samples']]['scripts'][0])
    function_to_call3 = getattr(module_to_import, 'load_samples')
    # params['query']={'project':}
    temp_samples=function_to_call3(params)
    for sample in temp_samples['samples']:
        if sample['in_project'] in project_ids:
            response['projects'][sample['in_project']]['sample_count']+=1
            response['projects'][sample['in_project']]['samples'].append(sample)

    cursor.close()
    conn.close()
    response['status']='success'
    return response

def ajax_create_project(request):
    response={}
    
    if not pylims.loggedin(request):
        response['error']='Must be logged in'
        return JsonResponse(response)
    
    data = json.loads(request.body)
    
    if not data['type']:
        response['error']='Unrecognized project type'
        return JsonResponse(response)
    if not data['id']:
        response['error']='Unrecognized project type id'
        return JsonResponse(response)
    if not data['name']:
        response['error']='Unrecognized project name'
        return JsonResponse(response)    
    
    

    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    
    if data['type']=='self':
        data['id']=int(request.session['userid'])

    cursor.execute("INSERT INTO projects (project_name, project_group_type, project_group_id, createdby) VALUES (%s, %s, %s, %s) RETURNING pid;", (data['name'],data['type'],data['id'],int(request.session['userid'])))
    try:
        data['newproject'] = cursor.fetchone()['pid']
        conn.commit()
        cursor.close()
        conn.close()
        response['status']='success'
    except TypeError:
        response['error']='Project creation failed.'
 
    response.update(data)
    return JsonResponse(response)
    

urlpatterns=[
    path('ajax_create_project/', ajax_create_project, name="ajax_create_project")
    ]