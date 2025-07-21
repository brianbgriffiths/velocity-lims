from django.urls import path, re_path
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

current_directory = os.path.dirname(os.path.abspath(__file__))
self = os.path.basename(current_directory)
scriptname = os.path.basename(__file__)

def load_samples(params):
    response={}
    
    if not 'userid' in params:
        response['error']='no userid'
        response['status']='failed'
        return response
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
   
    if 'query' in params and 'project' in params['query']:
        cursor.execute("SELECT * FROM samples WHERE in_project=%s", (int(params['query']['project']),))
        response['samples'] = cursor.fetchall()
        if response['samples']==[]:
            response['error']='project has not samples or samples not found'
            response['status']='failed'
            return response
        # if temp_project[0]['project_group_type']=='teams':
            # print('is team',params['userid'],int(params['query']['id']))
            # cursor.execute("SELECT * FROM user_teams AS ut JOIN teams ON teams.teamid=ut.team WHERE ut.user=%s AND ut.team=%s LIMIT 1", (params['userid'],int(temp_project[0]['project_group_id'])))
            # temp_team = cursor.fetchall()
            
            # if temp_team==[]:
                # response['error']='Not a member of team'
                # response['status']='failed'
                # return response

            # response['projects']=[temp_project[0] | temp_team[0]]
        # elif temp_project[0]['project_group_type']=='self':
            # if not temp_project[0]['project_group_id']==params['userid']:
                # response['error']='This is a private project'
                # response['status']='failed'
                # return response
            # response['projects']=temp_project
        cursor.close()
        conn.close()
        response['status']='success'
        return response

    cursor.execute("SELECT * FROM samples ORDER BY in_project;")
    response['samples'] = cursor.fetchall()    
    
    
    # if 'teams' in params['active_mods']:
        # cursor.execute("SELECT * FROM user_teams JOIN teams ON teamid=user_teams.team WHERE user_teams.user = %s::integer;", (int(params['userid']),))
        # response['teams'] = cursor.fetchall()
    
    # if 'departments' in params['active_mods']:
        # cursor.execute("SELECT * FROM user_departments JOIN departments ON deptid=user_departments.dept WHERE user_departments.user = %s::integer;", (int(params['userid']),))
        # response['departments'] = cursor.fetchall()
        
    # if 'organization' in params['active_mods']:
        # cursor.execute("SELECT * FROM user_organization JOIN organizations ON oid=user_organization.org WHERE user_organization.user = %s::integer;", (int(params['userid']),))
        # response['organization'] = cursor.fetchall()
    # cursor.close()
    # conn.close()
    response['status']='success'
    return response

def create_new_sample(request):
    accepted_permissions=['automations_configure']
    response={}
    
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    
    data = json.loads(request.body)

    if len(data['name'])<5:
        response['error']='New Step name not long enough'
        return JsonResponse(response)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM samples WHERE sample_name=%s LIMIT 1;",(data['name'],))
    
    result = cursor.fetchall()

    if len(result)>0:
        response['error']='sample with this name already exists'
        return JsonResponse(response)

    cursor.execute("INSERT INTO containers (container_name,type,location) VALUES (%s, %s, 0) RETURNING cid;",(data['name'],data['container']))
    response['new_container'] = cursor.fetchone()['cid']

    cursor.execute("INSERT INTO samples (sample_name,container_id,in_project,op,workflow) VALUES (%s, %s, %s, %s, %s) RETURNING sid;",(data['name'], response['new_container'], data['project'], request.session['userid'], data['workflow']))
    response['new_sample'] = cursor.fetchone()['sid']
    response['new_name'] = data['name']

    cursor.execute("INSERT INTO automation_subsample (host, created_by, in_container) VALUES (%s, %s, %s) RETURNING ssid;",(response['new_sample'],request.session['userid'],response['new_container']))
    response['new_subsample'] = cursor.fetchone()['ssid']

    cursor.execute("SELECT wfid, steps FROM automation_workflow WHERE wfid=%s LIMIT 1;",(data['workflow'],))
    result = cursor.fetchone()
    workflow = result['wfid']
    wfsteps = json.loads(result['steps'])

    cursor.execute("SELECT type FROM automation_step WHERE asid=%s LIMIT 1;",(wfsteps[0],))
    result = cursor.fetchone()

    print(f'found step {wfsteps[0]}, type: {result['type']}')

    cursor.execute("SELECT aqid FROM automation_step_queue WHERE workflow=%s and step=%s and pos=0 LIMIT 1;",(workflow,wfsteps[0]))
    result = cursor.fetchone()

    if not result==None:
        queue_id = result['aqid']
        print(f'Found Queue: {queue_id}')

        cursor.execute("INSERT INTO automation_queue (subsample,in_queue,added) VALUES (%s, %s, %s);",(response['new_subsample'],queue_id,int(time.time())))


    conn.commit()
    cursor.close()
    conn.close()

    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)

urlpatterns=[
   path("create_new_sample/", create_new_sample, name="create_new_sample"),
    ]