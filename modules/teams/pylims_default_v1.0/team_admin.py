from django.urls import path, re_path
from django.http import HttpResponse, HttpRequest, JsonResponse
import pylims, json, os
from pydantic import BaseModel, EmailStr, constr, ValidationError, validator
import psycopg
from psycopg.rows import dict_row
import bcrypt
import base64
import sys
from PIL import Image
from io import BytesIO

current_directory = os.path.dirname(os.path.abspath(__file__))
self = os.path.basename(current_directory)
scriptname = os.path.basename(__file__)

def admin_list_orgs(request):
    accepted_permissions=['teams_create','teams_edit','teams_assign']
    response={}
    
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    
    data = json.loads(request.body)

    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM organizations ORDER BY oid ASC")
    
    results = cursor.fetchall()
    print('organization count:',len(results))
    response['data']=results
    cursor.close()
    conn.close()

    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)

def admin_list_depts(request):
    accepted_permissions=['teams_create','teams_edit','teams_assign']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    data = json.loads(request.body)

    print(data)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM departments WHERE in_org=%s ORDER BY dept_name ASC",(int(data['id']),))
    
    results = cursor.fetchall()
    print('department count:',len(results))
    response['data']=results
    cursor.close()
    conn.close()

    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)

def admin_list_teams(request):
    accepted_permissions=['teams_create','teams_edit','teams_assign']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions,scriptname):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    data = json.loads(request.body)

    print(data)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM teams WHERE in_dept=%s ORDER BY team_name ASC",(int(data['id']),))
    
    results = cursor.fetchall()
    print('Team count:',len(results))
    response['data']=results
    cursor.close()
    conn.close()

    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)

def admin_add_team(request):
    accepted_permissions=['teams_create']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    data = json.loads(request.body)
    print(pylims.term(),pylims.info('team created'))
    print(data)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO teams (team_name, team_description, team_image, in_dept, creator) VALUES (%s::text, %s::text, %s::text, %s::integer, %s::integer);",(data['teamName'],data['teamDesc'],data['teamImg'],int(data['id']),request.session['userid']))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)
    
def admin_edit_team(request):
    accepted_permissions=['teams_edit']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    
    data = json.loads(request.body)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM departments WHERE teamid=%s::integer LIMIT 1;", (data['id'],));
    
    result = cursor.fetchone()
    response['data']=result
    cursor.close()
    conn.close()
    
    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)

def admin_upload_image(request):
    accepted_permissions=['teams_edit']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    
    data = json.loads(request.body)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    # print(data['id'],data['image'])
    cursor.execute("UPDATE teams SET team_image=%s::text WHERE teamid=%s::integer;", (data['image'], data['id']))
    conn.commit()
    cursor.close()
    conn.close()
    
    response['image']=data['image']
    
    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)

def admin_edit_save(request):
    accepted_permissions=['teams_edit']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    
    data = json.loads(request.body)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    cursor.execute("UPDATE teams SET team_description=%s::text, team_name=%s::text WHERE teamid=%s::integer;", (data['description'], data['name'], data['id']))
    conn.commit()
    cursor.close()
    conn.close()
    
    if not 'error' in response:
        response['msg_success']='Team updates saved'
        response['status']='success'
    return JsonResponse(response)

def admin_load_members(request):
    accepted_permissions=['teams_assign','assign']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    
    data = json.loads(request.body)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    cursor.execute("SELECT users.userid, users.username, users.email, ut.* FROM users LEFT JOIN user_teams AS ut ON ut.team=%s AND users.userid=ut.user ORDER BY users.email ASC;", (data['id'],))
    results = cursor.fetchall()
    print('user count:',len(results))
    response['data']=results
    cursor.close()
    conn.close()
    
    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)

def admin_assign_save(request):
    accepted_permissions=['teams_assign','assign']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    
    data = json.loads(request.body)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    cursor.execute("SELECT users.userid, users.username, users.email, ut.* FROM users LEFT JOIN user_teams AS ut ON users.userid=ut.user AND ut.team=%s::integer LEFT JOIN teams AS t ON t.teamid=ut.team ORDER BY users.email ASC;", (data['id'],))
    results = cursor.fetchall()
    print('user count:',len(results))
    
    for user in results:
        print('processing',user['userid'],user['utid'],str(user['userid']) in data['members'],str(user['userid']) in data['nonmembers'])
        if user['utid']==None and str(user['userid']) in data['members']:
            print('add!')
            cursor.execute("INSERT INTO user_teams (\"user\", team) VALUES (%s::integer, %s::integer);",(user['userid'],int(data['id'])))
        elif not user['utid']==None and str(user['userid']) in data['nonmembers']:
            print('remove')
            cursor.execute("DELETE FROM user_teams WHERE utid=%s::integer;",(user['utid'],))
        else:
            print('do nothing')
    
    conn.commit()
    cursor.close()
    conn.close()
    
    if not 'error' in response:
        response['msg_success']='Member assignments saved'
        response['status']='success'
    return JsonResponse(response)
    

urlpatterns=[
    path('admin_add_team/', admin_add_team, name="admin_add_team"),
    path('admin_list_depts/', admin_list_depts, name="admin_list_depts"),
    path('admin_list_orgs/', admin_list_orgs, name="admin_list_orgs"),
    path('admin_list_teams/', admin_list_teams, name="admin_list_teams"),
    path('admin_edit_team/', admin_edit_team, name="admin_edit_team"),
    path('admin_upload_image/', admin_upload_image, name="admin_upload_image"),
    path('admin_edit_save/', admin_edit_save, name="admin_edit_save"),
    path('admin_load_members/', admin_load_members, name="admin_load_members"),
    path('admin_assign_save/', admin_assign_save, name="admin_assign_save"),
    
    ]
    
