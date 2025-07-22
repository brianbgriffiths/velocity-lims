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

class EmailModel(BaseModel):
    email: EmailStr

def login_submit(request):
    data = json.loads(request.body)
    print(data)
    
    response={}
    selectdata={}
    if not 'logintype' in data or data['logintype']=='':
        response['error']='Login type not found'
        return JsonResponse(response)
    if not 'password' in data or data['password']=='':
        response['error']='Password not entered'
        return JsonResponse(response)
    if not 'login' in data or data['login']=='':
        response['error']='Login not entered'
        return JsonResponse(response)
    
    print('logging in with type',data['logintype'])
    
    if data['logintype']=='Email' and not data['login']=='root':  
        try:
            print('posted email:',data['login'])
            validated_email = EmailModel(email=data['login'])
            print('email is valid')
            selectdata['email']=data['login']
            selectdata['type']='email'
        except:
            response['error']='Email not valid'
            return JsonResponse(response)
    elif data['logintype']=='Email' and data['login']=='root':
        print('login is root')
        selectdata['email']=data['login']
        selectdata['type']='email'
        
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    column_name = selectdata['type']
    query = sql.SQL("SELECT userid, password FROM users WHERE {} = %s").format(sql.Identifier(column_name))

    cursor.execute(query, (data['login'],))

    # Fetching the hashed password from the result
    result = cursor.fetchone()
    print('result:',result)
    
    if result==None:
        response['error']='Email not found'
        return JsonResponse(response)
    
    if result and 'password' in result:
        hashed_password_from_db = result['password']
        valid_password = bcrypt.checkpw(data['password'].encode('utf-8'), hashed_password_from_db)
        print('valid password:',valid_password)
        if valid_password==False:
            response['error']='Password not valid'
            return JsonResponse(response)
    # bcrypt.checkpw(input_password.encode('utf-8'), hashed_password)
    request.session['userid']=result['userid']
    
    
    
    print('session',request.session.keys())
    if not 'error' in response:
        response['status']='success'
        response['msg_success']='Login successful'
    return JsonResponse(response)
