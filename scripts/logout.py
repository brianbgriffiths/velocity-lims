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

def logout_submit(request):
    data = json.loads(request.body)
    print(data)
    
    response={}
        
    request.session['userid']=None
    request.session.flush()
    print('session',request.session.keys())
    if not 'error' in response:
        response['status']='success'
        response['msg_success']='Logout successful'
    return JsonResponse(response)