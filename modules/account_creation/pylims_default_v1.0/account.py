from django.urls import path, re_path
from django.http import HttpResponse, HttpRequest, JsonResponse
import pylims, json, os
from pydantic import BaseModel, EmailStr, constr, ValidationError, validator
import psycopg
from psycopg.rows import dict_row
import bcrypt

current_directory = os.path.dirname(os.path.abspath(__file__))
self = os.path.basename(current_directory)

class EmailModel(BaseModel):
    email: EmailStr

class PasswordLengthModel(BaseModel):
    password: constr(min_length=8, max_length=32)

class ComplexPasswordModel(BaseModel):
    password: constr(min_length=8, max_length=32)

    @validator("password")
    def validate_password_complexity(cls, value):
        # Add your custom password complexity rules here
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isalpha() for char in value):
            raise ValueError("Password must contain at least one letter")
        # Add more rules as needed

        return value


def create_account(request):
    response={}
    print('ceating account',)
    mods = json.loads(pylims.get_setup_options())
    mod=mods['options']['account_creation'][self]
    print('mod',mod)
    insertdata={}
    data = json.loads(request.body)
    print(data)
    if mod['email']=='true':
        print('validate email')
        
        try:
            print('posted:',data['email'])
            validated_email = EmailModel(email=data['email'])
            print('email is valid')
            insertdata['email']=data['email']
        except:
            response['error']='Email not valid'
    if mod['password_complex']=='true':
        try:
            print('posted complex password',data['password'])
            validated_password = ComplexPasswordModel(password=data['password'])
            print('password is valid')
            hashedpass=bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
            print('hashed pass',hashedpass)
            insertdata['password']=hashedpass 
        except Exception as e:
            print('complex passsword not valid',e)
            response['error']='Password not valid'
    else:
        try:
            print('posted password',data['password'])
            validated_password = PasswordLengthModel(password=data['password'])
            print('password is valid')
            hashedpass=bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
            print('hashed pass',hashedpass)
            insertdata['password']=hashedpass
        except Exception as e:
            print('password not valid',e)
            response['error']='Password not valid'
    
    if 'error' in response:
        response['status']='failed'
        return JsonResponse(response)
    
    # connect to DB
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    # Execute the query with parameterized values
    cursor.execute("SELECT * FROM users WHERE email = %s LIMIT 1;", (data['email'],))

    result = cursor.fetchone()
    print('results',result)
    if not result==None:
        print('email already exists')
        response['error']='Account with this email already exists'
        response['status']='failed'
        return JsonResponse(response)
        
        
    print('creating user')


    # Build the dynamic part of the query
    columns = ', '.join(insertdata.keys())
    values = ', '.join(['%({})s'.format(key) for key in insertdata.keys()])

    # Construct the dynamic query
    query = "INSERT INTO users ({}) VALUES ({});".format(columns, values)
    
    # Execute the query with data
    cursor.execute(query, insertdata)
    conn.commit()

    # Close the cursor and connection
    cursor.close()
    conn.close()
    
    
    
    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)

urlpatterns=[
    path('create_account/', create_account, name="pylims_create_account"),
    ]
    
