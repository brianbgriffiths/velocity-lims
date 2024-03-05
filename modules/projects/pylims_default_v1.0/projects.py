from django.urls import path, re_path
from django.http import HttpResponse, HttpRequest, JsonResponse
import pylims, json, os
from pydantic import BaseModel, EmailStr, constr, ValidationError, validator
import psycopg
from psycopg import sql
from psycopg.rows import dict_row 
from psycopg.pq import Escaping

import bcrypt

current_directory = os.path.dirname(os.path.abspath(__file__))
self = os.path.basename(current_directory)
scriptname = os.path.basename(__file__)

def load_projects(params):
    response={}
    
    if not 'userid' in params:
        response['error']='no userid'
        response['status']='failed'
        return response
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    
    
    
    if 'query' in params and 'id' in params['query']:
        cursor.execute("SELECT * FROM projects WHERE pid=%s LIMIT 1", (int(params['query']['id']),))
        temp_project = cursor.fetchall()
        if temp_project==[]:
            response['error']='Project not found'
            response['status']='failed'
            return response
        if temp_project[0]['project_group_type']=='teams':
            print('is team',params['userid'],int(params['query']['id']))
            cursor.execute("SELECT * FROM user_teams AS ut JOIN teams ON teams.teamid=ut.team WHERE ut.user=%s AND ut.team=%s LIMIT 1", (params['userid'],int(temp_project[0]['project_group_id'])))
            temp_team = cursor.fetchall()
            temp_team[0]['owner']=temp_team[0]['team_name']
            if temp_team==[]:
                response['error']='Not a member of team'
                response['status']='failed'
                return response

            response['projects']=[temp_project[0] | temp_team[0]]
        elif temp_project[0]['project_group_type']=='self':
            if not temp_project[0]['project_group_id']==params['userid']:
                response['error']='This is a private project'
                response['status']='failed'
                return response
            response['projects']=temp_project
            
        if 'experiments' in params['active_mods']:
            pass
        
            
        cursor.close()
        conn.close()
        response['status']='success'
        return response
        
    
    
    if 'teams' in params['active_mods']:
        cursor.execute("SELECT * FROM user_teams JOIN teams ON teamid=user_teams.team WHERE user_teams.user = %s::integer;", (int(params['userid']),))
        response['teams'] = cursor.fetchall()
    
    if 'departments' in params['active_mods']:
        cursor.execute("SELECT * FROM user_departments JOIN departments ON deptid=user_departments.dept WHERE user_departments.user = %s::integer;", (int(params['userid']),))
        response['departments'] = cursor.fetchall()
        
    if 'organization' in params['active_mods']:
        cursor.execute("SELECT * FROM user_organization JOIN organizations ON oid=user_organization.org WHERE user_organization.user = %s::integer;", (int(params['userid']),))
        response['organization'] = cursor.fetchall()
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
        reponse['error']='Project creation failed.'
 
    response.update(data)
    return JsonResponse(response)
    

urlpatterns=[
    path('ajax_create_project/', ajax_create_project, name="ajax_create_project")
    ]