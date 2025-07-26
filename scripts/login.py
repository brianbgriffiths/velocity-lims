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
    
    if data['logintype']=='email' and not data['login']=='root':  
        try:
            print('posted email:',data['login'])
            validated_email = EmailModel(email=data['login'])
            print('email is valid')
            selectdata['email']=data['login']
            selectdata['type']='email'
        except:
            response['error']='Email not valid'
            return JsonResponse(response)
    elif data['logintype']=='email' and data['login']=='root':
        print('login is root')
        selectdata['email']=data['login']
        selectdata['type']='email'
        
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    column_name = selectdata['type']
    query = sql.SQL("SELECT userid, password FROM velocity.accounts WHERE {} = %s").format(sql.Identifier(column_name))

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

    # Load roles and permissions for the user
    try:
        # Since there's no direct user-role relationship yet, we'll need to create one
        # For now, let's check if there's a roles column in accounts table or create a user_roles table
        
        user_permissions = {}
        user_role_ids = []
        
        # Try to find user roles - check if accounts table has a roles column
        try:
            cursor.execute("SELECT roles FROM velocity.accounts WHERE userid = %s", (result['userid'],))
            user_roles_result = cursor.fetchone()
            if user_roles_result and user_roles_result.get('roles'):
                # roles is a JSON array of role IDs
                if isinstance(user_roles_result['roles'], str):
                    user_role_ids = json.loads(user_roles_result['roles'])
                elif isinstance(user_roles_result['roles'], list):
                    user_role_ids = user_roles_result['roles']
                print(f"Found roles in accounts table for user {result['userid']}: {user_role_ids}")
        except Exception as roles_error:
            # roles column doesn't exist in accounts table
            print(f"No roles column in accounts table: {roles_error}")
            
            # Try user_roles junction table
            try:
                cursor.execute("SELECT role_id FROM velocity.user_roles WHERE user_id = %s", (result['userid'],))
                user_roles_result = cursor.fetchall()
                user_role_ids = [row['role_id'] for row in user_roles_result]
                print(f"Found roles in user_roles table for user {result['userid']}: {user_role_ids}")
            except Exception as junction_error:
                print(f"No user_roles table found: {junction_error}")
                # No roles assigned to user yet
                user_role_ids = []
        
        # If user has roles, get their permissions
        if user_role_ids:
            # Get roles and their permission sets
            placeholders = ','.join(['%s'] * len(user_role_ids))
            roles_query = f"SELECT rid, permission_set FROM velocity.roles WHERE rid IN ({placeholders})"
            cursor.execute(roles_query, user_role_ids)
            user_roles = cursor.fetchall()
            
            # Collect all permission IDs from all roles
            all_permission_ids = set()
            for role in user_roles:
                permission_set = role['permission_set']
                if isinstance(permission_set, str):
                    try:
                        permission_ids = json.loads(permission_set)
                    except:
                        permission_ids = []
                elif isinstance(permission_set, list):
                    permission_ids = permission_set
                else:
                    permission_ids = []
                
                # Add all permission IDs to our set
                all_permission_ids.update(permission_ids)
            
            print(f"All permission IDs for user: {all_permission_ids}")
            
            # Convert permission IDs to permission names
            if all_permission_ids:
                placeholders = ','.join(['%s'] * len(all_permission_ids))
                permissions_query = f"SELECT pid, permission FROM velocity.permissions WHERE pid IN ({placeholders})"
                cursor.execute(permissions_query, list(all_permission_ids))
                permissions_result = cursor.fetchall()
                
                # Build the final permissions dictionary with permission names as keys
                for perm in permissions_result:
                    user_permissions[perm['permission']] = True
            
            print(f"Final user permissions: {user_permissions}")
        else:
            print(f"No roles assigned to user {result['userid']}")
        
        # Store permissions in session
        request.session['permissions'] = user_permissions
            
    except Exception as e:
        print(f"Error loading user permissions: {str(e)}")
        # Set empty permissions on error
        request.session['permissions'] = {}
    
    print('session',request.session.keys())
    if not 'error' in response:
        response['status']='success'
        response['msg_success']='Login successful'
    return JsonResponse(response)
