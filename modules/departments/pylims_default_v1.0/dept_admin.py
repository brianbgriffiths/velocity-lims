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

current_directory = os.path.dirname(os.path.abspath(__file__))
self = os.path.basename(current_directory)

def admin_list_orgs(request):
    accepted_permissions=['departments_create','departments_edit']
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
    accepted_permissions=['departments_assign','departments_create','departments_edit']
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

def admin_add_dept(request):
    accepted_permissions=['departments_create']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    data = json.loads(request.body)
    print(pylims.term(),pylims.info('department created'))
    print(data)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO departments (dept_name, dept_description, dept_image, in_org, creator) VALUES (%s::text, %s::text, %s::text, %s::integer, %s::integer);",(data['deptName'],data['deptDesc'],data['deptImg'],int(data['id']),request.session['userid']))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)
    
def admin_edit_dept(request):
    accepted_permissions=['departments_edit']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    
    data = json.loads(request.body)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM departments WHERE deptid=%s::integer LIMIT 1;", (data['id'],));
    
    result = cursor.fetchone()
    response['data']=result
    cursor.close()
    conn.close()
    
    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)

def admin_upload_image(request):
    accepted_permissions=['departments_edit']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    
    data = json.loads(request.body)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    # print(data['id'],data['image'])
    cursor.execute("UPDATE departments SET dept_image=%s::text WHERE deptid=%s::integer;", (data['image'], data['id']))
    conn.commit()
    cursor.close()
    conn.close()
    
    response['image']=data['image']
    
    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)

def admin_edit_save(request):
    accepted_permissions=['departments_edit']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    
    data = json.loads(request.body)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    cursor.execute("UPDATE departments SET dept_description=%s::text, dept_name=%s::text WHERE deptid=%s::integer;", (data['description'], data['name'], data['id']))
    conn.commit()
    cursor.close()
    conn.close()
    
    if not 'error' in response:
        response['msg_success']='Department updates saved'
        response['status']='success'
    return JsonResponse(response)

def admin_load_members(request):
    accepted_permissions=['departments_assign','assign']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    
    data = json.loads(request.body)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    cursor.execute("SELECT users.userid, users.username, users.email, ud.* FROM users LEFT JOIN user_departments AS ud ON ud.dept=%s AND users.userid=ud.user ORDER BY users.email ASC;", (data['id'],))
    results = cursor.fetchall()
    print('user count:',len(results))
    response['data']=results
    cursor.close()
    conn.close()
    
    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)

def admin_assign_save(request):
    accepted_permissions=['departments_assign','assign']
    response={}
    if not pylims.adminauthmatch(pylims.loaduser_admin(request.session['userid']),accepted_permissions):
        response['error']='Insufficient permissions'
        return JsonResponse(response)
    
    data = json.loads(request.body)
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    cursor.execute("SELECT users.userid, users.username, users.email, ud.* FROM users LEFT JOIN user_departments AS ud ON users.userid=ud.user AND ud.dept=%s::integer LEFT JOIN departments AS d ON d.deptid=ud.dept ORDER BY users.email ASC;", (data['id'],))
    results = cursor.fetchall()
    print('user count:',len(results))
    
    for user in results:
        print('processing',user['userid'],user['udid'],str(user['userid']) in data['members'],str(user['userid']) in data['nonmembers'])
        if user['udid']==None and str(user['userid']) in data['members']:
            print('add!')
            cursor.execute("INSERT INTO user_departments (\"user\", dept) VALUES (%s::integer, %s::integer);",(user['userid'],int(data['id'])))
        elif not user['udid']==None and str(user['userid']) in data['nonmembers']:
            print('remove')
            cursor.execute("DELETE FROM user_departments WHERE udid=%s::integer;",(user['udid'],))
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
    path('admin_add_dept/', admin_add_dept, name="admin_add_dept"),
    path('admin_list_depts/', admin_list_depts, name="admin_list_depts"),
    path('admin_list_orgs/', admin_list_orgs, name="admin_list_orgs"),
    path('admin_edit_dept/', admin_edit_dept, name="admin_edit_dept"),
    path('admin_upload_image/', admin_upload_image, name="admin_upload_image"),
    path('admin_edit_save/', admin_edit_save, name="admin_edit_save"),
    path('admin_load_members/', admin_load_members, name="admin_load_members"),
    path('admin_assign_save/', admin_assign_save, name="admin_assign_save"),
    
    ]
    
