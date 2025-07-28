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

def load_user_permissions(request, user_id):
    """
    Load user roles and permissions into the session.
    
    Args:
        request: Django HttpRequest object
        user_id: The user ID to load permissions for
    """
    from settings import settings
    
    try:
        # Connect to database
        conn = psycopg.connect(
            host=settings.DATABASES['default']['HOST'],
            port=settings.DATABASES['default']['PORT'],
            dbname=settings.DATABASES['default']['NAME'],
            user=settings.DATABASES['default']['USER'],
            password=settings.DATABASES['default']['PASSWORD'],
            row_factory=dict_row
        )
        cursor = conn.cursor()
        
        user_permissions = {}
        user_role_ids = []
        
        # Try to find user roles - check if accounts table has a roles column
        try:
            cursor.execute("SELECT roles FROM velocity.accounts WHERE userid = %s", (user_id,))
            user_roles_result = cursor.fetchone()
            if user_roles_result and user_roles_result.get('roles'):
                # roles is a JSON array of role IDs
                user_role_ids = json.loads(user_roles_result['roles']) if isinstance(user_roles_result['roles'], str) else user_roles_result['roles']
        except Exception as roles_column_error:
            print(f"No roles column in accounts table: {roles_column_error}")
            # Try user_roles junction table
            try:
                cursor.execute("SELECT role_id FROM velocity.user_roles WHERE user_id = %s", (user_id,))
                junction_results = cursor.fetchall()
                user_role_ids = [row['role_id'] for row in junction_results]
            except Exception as junction_error:
                print(f"No user_roles junction table: {junction_error}")
                user_role_ids = []
        
        # If user has roles, get their permissions
        if user_role_ids:
            print(f"User {user_id} has roles: {user_role_ids}")
            
            # Get all permission sets for the user's roles
            placeholders = ','.join(['%s'] * len(user_role_ids))
            roles_query = f"SELECT rid, permission_set FROM velocity.roles WHERE rid IN ({placeholders})"
            cursor.execute(roles_query, user_role_ids)
            roles_result = cursor.fetchall()
            
            # Collect all unique permission IDs from all roles
            all_permission_ids = set()
            for role in roles_result:
                if role['permission_set']:
                    try:
                        permission_ids = json.loads(role['permission_set']) if isinstance(role['permission_set'], str) else role['permission_set']
                        if isinstance(permission_ids, list):
                            all_permission_ids.update(permission_ids)
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"Error parsing permission_set for role {role['rid']}: {e}")
            
            # Get the actual permission names
            if all_permission_ids:
                placeholders = ','.join(['%s'] * len(all_permission_ids))
                permissions_query = f"SELECT pid, permission FROM velocity.permissions WHERE pid IN ({placeholders})"
                cursor.execute(permissions_query, list(all_permission_ids))
                permissions_result = cursor.fetchall()
                
                # Build the final permissions dictionary with permission names as keys
                for perm in permissions_result:
                    user_permissions[perm['permission']] = True
            
            # Create meta permissions based on prefixes
            permission_prefixes = set()
            for permission_name in user_permissions.keys():
                if '_' in permission_name:
                    prefix = permission_name.split('_')[0]
                    permission_prefixes.add(prefix)
            
            # Add "any_[prefix]" meta permissions
            for prefix in permission_prefixes:
                meta_permission = f"any_{prefix}"
                user_permissions[meta_permission] = True
                print(f"Added meta permission: {meta_permission}")
            
            print(f"Final user permissions: {user_permissions}")
        else:
            print(f"No roles assigned to user {user_id}")
        
        # Store permissions in session
        request.session['permissions'] = user_permissions
        
        cursor.close()
        conn.close()
            
    except Exception as e:
        print(f"Error loading user permissions: {str(e)}")
        # Set empty permissions on error
        request.session['permissions'] = {}

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
    query = sql.SQL("SELECT userid, password, activated, email, username FROM velocity.accounts WHERE {} = %s").format(sql.Identifier(column_name))

    cursor.execute(query, (data['login'],))

    # Fetching the hashed password from the result
    result = cursor.fetchone()
    print('result:',result)
    
    if result==None:
        response['error']='Email not found'
        return JsonResponse(response)
    
    # Check if account is activated
    if not result.get('activated', False):
        print('Account not activated, redirecting to code entry')
        cursor.close()
        conn.close()
        response['status'] = 'activation_required'
        response['redirect_url'] = '/enter_activation_code'
        response['email'] = result['email']
        return JsonResponse(response)
    
    if result and 'password' in result:
        hashed_password_from_db = result['password']
        if hashed_password_from_db is None:
            response['error']='Please set a password for your account. Contact an administrator.'
            return JsonResponse(response)
            
        valid_password = bcrypt.checkpw(data['password'].encode('utf-8'), hashed_password_from_db)
        print('valid password:',valid_password)
        if valid_password==False:
            response['error']='Password not valid'
            return JsonResponse(response)
    # bcrypt.checkpw(input_password.encode('utf-8'), hashed_password)
    request.session['userid']=result['userid']

    # Load roles and permissions for the user
    load_user_permissions(request, result['userid'])
    
    cursor.close()
    conn.close()
    
    print('session',request.session.keys())
        
    if not 'error' in response:
        response['status']='success'
        response['msg_success']='Login successful'
    return JsonResponse(response)
