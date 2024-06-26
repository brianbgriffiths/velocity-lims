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


    

urlpatterns=[
    path('admin_list_orgs/', admin_list_orgs, name="admin_list_orgs"),
    ]
    
