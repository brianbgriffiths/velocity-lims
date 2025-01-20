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

def load_containers(params):
    # print(pylims.term(),'load containers')
    response={}
    
    if not 'userid' in params:
        response['error']='no userid'
        response['status']='failed'
        return response
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    
    cursor.execute("SELECT cid, container_name as name, prefix, spots, rows, columns FROM container_types WHERE can_start=true ORDER BY name ASC;")
    response['containers'] = cursor.fetchall()

    cursor.close()
    conn.close()
    if not 'error' in response:
        response['status']='success'
    return response


urlpatterns=[
   
    ]