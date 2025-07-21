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

def admin_list_orgs(request):
    accepted_permissions=['organizations_edit']
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

def admin_edit_org(request):
    accepted_permissions=['organizations_edit']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    
    data = json.loads(request.body)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM organizations WHERE oid=%s::integer LIMIT 1;", (data['id'],));
    
    result = cursor.fetchone()
    response['data']=result
    cursor.close()
    conn.close()
    
    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)

def admin_upload_image(request):
    accepted_permissions=['organizations_edit']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    
    data = json.loads(request.body)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    # print(data['id'],data['image'])
    cursor.execute("UPDATE organizations SET image=%s::text WHERE oid=%s::integer;", (data['image'], data['id']))
    conn.commit()
    cursor.close()
    conn.close()
    
    response['image']=data['image']
    
    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)

def admin_edit_save(request):
    accepted_permissions=['organizations_edit']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    
    data = json.loads(request.body)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    cursor.execute("UPDATE organizations SET description=%s::text, organization_name=%s::text WHERE oid=%s::integer;", (data['description'], data['name'], data['id']))
    conn.commit()
    cursor.close()
    conn.close()
    
    if not 'error' in response:
        response['msg_success']='Organization updates saved'
        response['status']='success'
    return JsonResponse(response)

def admin_load_members(request):
    accepted_permissions=['organizations_assign','assign']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    
    data = json.loads(request.body)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    cursor.execute("SELECT users.userid, users.username, users.email, uo.*, uaid FROM users LEFT JOIN user_organization AS uo ON users.userid=uo.user AND uo.org=%s::integer LEFT JOIN organizations AS o ON o.oid=uo.org LEFT JOIN user_admin AS ua ON ua.user=users.userid AND ua.permission=10 AND ua.value=%s ORDER BY users.email ASC;", (data['id'],str(data['id'])))
    results = cursor.fetchall()
    print('user count:',len(results))
    response['data']=results
    cursor.close()
    conn.close()
    
    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)

def admin_assign_save(request):
    accepted_permissions=['organizations_assign','admin_assign']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    
    data = json.loads(request.body)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    cursor.execute("SELECT users.userid, users.username, users.email, uo.* FROM users LEFT JOIN user_organization AS uo ON users.userid=uo.user AND uo.org=%s::integer LEFT JOIN organizations AS o ON o.oid=uo.org ORDER BY users.email ASC;", (data['id'],))
    results = cursor.fetchall()
    print('user count:',len(results))
    
    for user in results:
        print('processing',user['userid'],user['uoid'],str(user['userid']) in data['members'],str(user['userid']) in data['nonmembers'])
        if user['uoid']==None and str(user['userid']) in data['members']:
            print('add!')
            cursor.execute("INSERT INTO user_organization (\"user\", org) VALUES (%s::integer, %s::integer);",(user['userid'],int(data['id'])))          
        elif not user['uoid']==None and str(user['userid']) in data['nonmembers']:
            print('remove')
            cursor.execute("DELETE FROM user_organization WHERE uoid=%s::integer;",(user['uoid'],))
        else:
            print('do nothing')
        
        cursor.execute("SELECT uaid FROM user_admin WHERE \"user\"=%s AND permission=10 AND value=%s LIMIT 1;",(user['userid'],str(data['id'])))
        result = cursor.fetchone()
        
        if str(user['userid']) in data['dept']:
            if result==None:
                cursor.execute("INSERT INTO user_admin (\"user\",permission,value) VALUES (%s,10,%s);",(user['userid'],str(data['id'])))
        elif str(user['userid']) in data['nondept']:
            if not result==None:
                cursor.execute("DELETE FROM user_admin WHERE \"user\"=%s AND permission=10 AND value=%s",(user['userid'],str(data['id'])))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    if not 'error' in response:
        response['msg_success']='Member assignments saved'
        response['status']='success'
    return JsonResponse(response)
    

urlpatterns=[
    path('admin_list_orgs/', admin_list_orgs, name="admin_list_orgs"),
    path('admin_edit_org/', admin_edit_org, name="admin_edit_org"),
    path('admin_upload_image/', admin_upload_image, name="admin_upload_image"),
    path('admin_edit_save/', admin_edit_save, name="admin_edit_save"),
    path('admin_load_members/', admin_load_members, name="admin_load_members"),
    path('admin_assign_save/', admin_assign_save, name="admin_assign_save"),
    ]
    
