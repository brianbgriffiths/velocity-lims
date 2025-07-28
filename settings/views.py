from django.contrib import admin
from django.urls import path, re_path, reverse
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpRequest, JsonResponse
from django.template.defaulttags import register
from django.conf.urls import include
from django.views.decorators.csrf import csrf_exempt
import json, os, sys, subprocess, datetime
from pathlib import Path
from settings import settings
from django.template.loader import get_template
from functools import wraps
import pylims
import psycopg
from psycopg import sql
from psycopg.rows import dict_row 
from psycopg.pq import Escaping

def is_user_logged_in(request):
    """
    Check if the user is logged in by verifying if userid is set in the session.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        bool: True if user is logged in (userid exists in session), False otherwise
    """
    userid = request.session.get('userid', None)
    if userid is None:
        return False
    return True

def has_permission(request, permission_name):
    """
    Check if the current user has a specific permission.
    
    Args:
        request: Django HttpRequest object
        permission_name: String name of the permission to check
        
    Returns:
        bool: True if user has the permission, False otherwise
    """
    if not is_user_logged_in(request):
        return False
    
    permissions = request.session.get('permissions', {})
    return permissions.get(permission_name, False)

def get_user_permissions(request):
    """
    Get all permissions for the current user.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        dict: Dictionary of permissions where keys are permission names and values are True
    """
    if not is_user_logged_in(request):
        return {}
    
    return request.session.get('permissions', {})

def login_required(view_func):
    """
    Decorator that requires a user to be logged in to access a view.
    
    If the user is not logged in, they will be redirected to the login page.
    
    Usage:
        @login_required
        def my_view(request):
            # This view is only accessible to logged-in users
            pass
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_user_logged_in(request):
            return redirect('show_login')  # Redirect to login page
        return view_func(request, *args, **kwargs)
    return wrapper



def handlePost(request):
    if request.method == 'POST':
        try:
            json_data = json.loads(request.body)
            return 200
        except json.JSONDecodeError as e:
            return 400
    return 405
    

def home(request):
    context={}
    context['info']=[]
    with open("VERSION", 'r') as file:
        context['info'].append(['Velocity LIMS Version',file.read()])
    context['info'].append(['Python Version',".".join(sys.version.split()[0].split('.')[:2])])
    
    # Add sample count to info
    try:
        conn = psycopg.connect(
            dbname=pylims.dbname, 
            user=pylims.dbuser, 
            password=pylims.dbpass, 
            host=pylims.dbhost, 
            port=pylims.dbport, 
            row_factory=dict_row
        )
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT reltuples::BIGINT AS total_requisitions FROM pg_class WHERE oid = 'velocity.requisitions'::regclass;")
            velocity_result = cursor.fetchone()
            context['info'].append(['Requisition Count', f"{velocity_result['total_requisitions']:,}"])
        except:
            context['info'].append(['Requisition Count', 0])
        
        try:
            cursor.execute("SELECT reltuples::BIGINT AS total_specimens FROM pg_class WHERE oid = 'velocity.specimens'::regclass;")
            velocity_result = cursor.fetchone()
            context['info'].append(['Specimen Count', f"{velocity_result['total_specimens']:,}"])
        except:
            context['info'].append(['Specimen Count', 0])

        

    except Exception as e:
        context['info'].append(['Database Stats', f'Error: {str(e)}'])

    if not is_user_logged_in(request):
        context['userid'] = None
    else:
        context['userid'] = request.session.get('userid', None)
        context['full_name'] = request.session.get('full_name', None)
        context['permissions'] = get_user_permissions(request)
    return render(request, 'index.html', context)

def show_login(request):
    context = {}
    return render(request, 'login.html', context)

def enter_activation_code(request):
    """
    Show the activation code entry page for unactivated accounts.
    """
    context = {}
    return render(request, 'enter_activation_code.html', context)

def activate_account(request):
    """
    Activate an account using the activation code.
    
    Expected data:
    {
        "email": "user@example.com",
        "activation_code": "ABC12345"
    }
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email', '').strip()
            activation_code = data.get('activation_code', '').strip().upper()
            
            if not email or not activation_code:
                return JsonResponse({'error': 'Email and activation code are required'}, status=400)
            
            try:
                conn = psycopg.connect(
                    host=settings.DATABASES['default']['HOST'],
                    port=settings.DATABASES['default']['PORT'],
                    dbname=settings.DATABASES['default']['NAME'],
                    user=settings.DATABASES['default']['USER'],
                    password=settings.DATABASES['default']['PASSWORD'],
                    row_factory=dict_row
                )
                cursor = conn.cursor()
                
                # Look up user by email and activation code (stored in activation_code field)
                cursor.execute("""
                    SELECT userid, username, full_name, roles, activated, activation_code
                    FROM velocity.accounts 
                    WHERE email = %s
                """, (email,))
                
                user = cursor.fetchone()
                
                if user:
                    if user['activated']:
                        return JsonResponse({'error': 'Account is already activated'}, status=400)
                    
                    # Check if the activation code matches
                    stored_code = user['activation_code']
                    
                    if stored_code != activation_code:
                        return JsonResponse({'error': 'Invalid activation code'}, status=400)
                    
                    # Activate the account and clear the activation code
                    cursor.execute("""
                        UPDATE velocity.accounts 
                        SET activated = TRUE, activation_code = NULL 
                        WHERE userid = %s
                    """, (user['userid'],))
                    
                    # Set session variables to log the user in
                    request.session['userid'] = user['userid']
                    request.session['email'] = email
                    request.session['username'] = user['username']
                    request.session['full_name'] = user['full_name']
                    
                    # Load user permissions
                    from scripts.login import load_user_permissions
                    load_user_permissions(request, user['userid'])
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    print(f"Account activated for user {user['username']} ({email})")
                    return JsonResponse({'status': 'success', 'message': 'Account activated successfully'}, status=200)
                else:
                    cursor.close()
                    conn.close()
                    return JsonResponse({'error': 'Invalid activation code or email'}, status=400)
                    
            except Exception as e:
                return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)

def resend_activation_code(request):
    """
    Resend the activation code to the user's email.
    
    Expected data:
    {
        "email": "user@example.com"
    }
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email', '').strip()
            
            if not email:
                return JsonResponse({'error': 'Email is required'}, status=400)
            
            try:
                conn = psycopg.connect(
                    host=settings.DATABASES['default']['HOST'],
                    port=settings.DATABASES['default']['PORT'],
                    dbname=settings.DATABASES['default']['NAME'],
                    user=settings.DATABASES['default']['USER'],
                    password=settings.DATABASES['default']['PASSWORD'],
                    row_factory=dict_row
                )
                cursor = conn.cursor()
                
                # Look up user by email
                cursor.execute("""
                    SELECT userid, full_name, activation_code, activated 
                    FROM velocity.accounts 
                    WHERE email = %s
                """, (email,))
                
                user = cursor.fetchone()
                
                if user:
                    if user['activated']:
                        return JsonResponse({'error': 'Account is already activated'}, status=400)
                    
                    if not user['activation_code']:
                        # Generate new activation code
                        import random
                        import string
                        new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                        
                        # Update the activation code
                        cursor.execute("""
                            UPDATE velocity.accounts 
                            SET activation_code = %s 
                            WHERE userid = %s
                        """, (new_code, user['userid']))
                        
                        activation_code = new_code
                    else:
                        activation_code = user['activation_code']
                    
                    # Send activation email
                    try:
                        send_login_email(user['full_name'], email, activation_code)
                        email_status = "sent successfully"
                    except Exception as email_error:
                        print(f"Warning: Failed to send email: {email_error}")
                        email_status = "failed to send"
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    if email_status == "sent successfully":
                        return JsonResponse({'status': 'success', 'message': 'Activation code resent to your email'}, status=200)
                    else:
                        return JsonResponse({'error': 'Failed to send activation email'}, status=500)
                else:
                    cursor.close()
                    conn.close()
                    return JsonResponse({'error': 'Email not found'}, status=404)
                    
            except Exception as e:
                return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def show_logout(request):
    context = {}
    context['userid'] = request.session.get('userid', None)
    context['full_name'] = request.session.get('full_name', None)
    return render(request, 'logout.html', context)

@login_required
def view_settings(request):
    context = {}
    context['userid'] = request.session.get('userid', None)
    context['full_name'] = request.session.get('full_name', None)
    context['permissions'] = get_user_permissions(request)

    return render(request, 'settings.html', context)

@login_required
def settings_operators(request):
    context = {}
    context['userid'] = request.session.get('userid', None)
    context['full_name'] = request.session.get('full_name', None)
    context['permissions'] = get_user_permissions(request)

    return render(request, 'settings_operators.html', context)

@login_required
def settings_roles(request):
    context = {}
    context['userid'] = request.session.get('userid', None)
    context['full_name'] = request.session.get('full_name', None)
    context['permissions'] = get_user_permissions(request)

    # Fetch roles from the database
    try:
        conn = psycopg.connect(
            dbname=pylims.dbname, 
            user=pylims.dbuser, 
            password=pylims.dbpass, 
            host=pylims.dbhost, 
            port=pylims.dbport, 
            row_factory=dict_row
        )
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM velocity.roles;")
        roles = cursor.fetchall()

        cursor.execute("SELECT * FROM velocity.permissions;")
        permissions = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        context['roles'] = roles
        context['role_permissions'] = permissions
    except Exception as e:
        context['error'] = f"Error fetching roles: {str(e)}"

    return render(request, 'settings_roles.html', context)

@login_required
def save_role(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            role_name = data.get('role_name')
            permission_set = data.get('permission_set', [])

            if not role_name:
                return JsonResponse({'error': 'Role name is required'}, status=400)

            if not permission_set:
                return JsonResponse({'error': 'At least one permission must be selected'}, status=400)

            try:
                conn = psycopg.connect(
                    dbname=pylims.dbname,
                    user=pylims.dbuser,
                    password=pylims.dbpass,
                    host=pylims.dbhost,
                    port=pylims.dbport,
                    row_factory=dict_row
                )
                cursor = conn.cursor()

                # Convert permission_set to JSON string
                permission_set_json = json.dumps(permission_set)

                # Insert role in the database - using correct column names
                cursor.execute("""
                    INSERT INTO velocity.roles (role_name, permission_set)
                    VALUES (%s, %s)
                    RETURNING rid
                """, (role_name, permission_set_json))
                
                result = cursor.fetchone()
                role_id = result['rid']

                conn.commit()
                cursor.close()
                conn.close()

                return JsonResponse({'status': 'success', 'role_id': role_id}, status=200)
            except Exception as e:
                return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def edit_role(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            role_id = data.get('role_id')
            role_name = data.get('role_name')
            permission_set = data.get('permission_set', [])

            if not role_id:
                return JsonResponse({'error': 'Role ID is required'}, status=400)

            if not role_name:
                return JsonResponse({'error': 'Role name is required'}, status=400)

            if not permission_set:
                return JsonResponse({'error': 'At least one permission must be selected'}, status=400)

            try:
                conn = psycopg.connect(
                    dbname=pylims.dbname,
                    user=pylims.dbuser,
                    password=pylims.dbpass,
                    host=pylims.dbhost,
                    port=pylims.dbport,
                    row_factory=dict_row
                )
                cursor = conn.cursor()

                # Convert permission_set to JSON string
                permission_set_json = json.dumps(permission_set)

                # Update role in the database
                cursor.execute("""
                    UPDATE velocity.roles 
                    SET role_name = %s, permission_set = %s 
                    WHERE rid = %s
                """, (role_name, permission_set_json, role_id))

                if cursor.rowcount == 0:
                    return JsonResponse({'error': 'Role not found'}, status=404)

                conn.commit()
                cursor.close()
                conn.close()

                return JsonResponse({'status': 'success'}, status=200)
            except Exception as e:
                return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def delete_role(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            role_id = data.get('role_id')

            if not role_id:
                return JsonResponse({'error': 'Role ID is required'}, status=400)

            try:
                conn = psycopg.connect(
                    dbname=pylims.dbname,
                    user=pylims.dbuser,
                    password=pylims.dbpass,
                    host=pylims.dbhost,
                    port=pylims.dbport,
                    row_factory=dict_row
                )
                cursor = conn.cursor()

                # Delete role from the database
                cursor.execute("""
                    DELETE FROM velocity.roles 
                    WHERE rid = %s
                """, (role_id,))

                if cursor.rowcount == 0:
                    return JsonResponse({'error': 'Role not found'}, status=404)

                conn.commit()
                cursor.close()
                conn.close()

                return JsonResponse({'status': 'success'}, status=200)
            except Exception as e:
                return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def assign_user_roles(request):
    """
    Assign roles to a user. This will create the user-role relationship.
    
    Expected data:
    {
        "user_id": 123,
        "role_ids": [1, 2, 3]
    }
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            role_ids = data.get('role_ids', [])

            if not user_id:
                return JsonResponse({'error': 'User ID is required'}, status=400)

            try:
                conn = psycopg.connect(
                    dbname=pylims.dbname,
                    user=pylims.dbuser,
                    password=pylims.dbpass,
                    host=pylims.dbhost,
                    port=pylims.dbport,
                    row_factory=dict_row
                )
                cursor = conn.cursor()

                # Try to update roles column in accounts table first
                try:
                    roles_json = json.dumps(role_ids)
                    cursor.execute("UPDATE velocity.accounts SET roles = %s WHERE userid = %s", (roles_json, user_id))
                    
                    if cursor.rowcount == 0:
                        return JsonResponse({'error': 'User not found'}, status=404)
                    
                    print(f"Updated roles in accounts table for user {user_id}: {role_ids}")
                    
                except Exception as accounts_error:
                    print(f"Accounts table doesn't have roles column: {accounts_error}")
                    
                    # Try user_roles junction table instead
                    try:
                        # First, delete existing role assignments
                        cursor.execute("DELETE FROM velocity.user_roles WHERE user_id = %s", (user_id,))
                        
                        # Insert new role assignments
                        for role_id in role_ids:
                            cursor.execute("INSERT INTO velocity.user_roles (user_id, role_id) VALUES (%s, %s)", (user_id, role_id))
                        
                        print(f"Updated roles in user_roles table for user {user_id}: {role_ids}")
                        
                    except Exception as junction_error:
                        return JsonResponse({'error': f'No user-role relationship table found. Please create either a "roles" column in velocity.accounts or a velocity.user_roles table. Error: {str(junction_error)}'}, status=500)

                conn.commit()
                cursor.close()
                conn.close()

                return JsonResponse({'status': 'success', 'message': f'Assigned {len(role_ids)} roles to user {user_id}'}, status=200)
                
            except Exception as e:
                return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def get_user_roles(request):
    """
    Get roles assigned to a user.
    
    Expected data:
    {
        "user_id": 123
    }
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')

            if not user_id:
                return JsonResponse({'error': 'User ID is required'}, status=400)

            try:
                conn = psycopg.connect(
                    dbname=pylims.dbname,
                    user=pylims.dbuser,
                    password=pylims.dbpass,
                    host=pylims.dbhost,
                    port=pylims.dbport,
                    row_factory=dict_row
                )
                cursor = conn.cursor()

                user_role_ids = []
                
                # Try to get roles from accounts table first
                try:
                    cursor.execute("SELECT roles FROM velocity.accounts WHERE userid = %s", (user_id,))
                    result = cursor.fetchone()
                    if result and result.get('roles'):
                        if isinstance(result['roles'], str):
                            user_role_ids = json.loads(result['roles'])
                        elif isinstance(result['roles'], list):
                            user_role_ids = result['roles']
                        
                except Exception:
                    # Try user_roles junction table
                    try:
                        cursor.execute("SELECT role_id FROM velocity.user_roles WHERE user_id = %s", (user_id,))
                        results = cursor.fetchall()
                        user_role_ids = [row['role_id'] for row in results]
                    except Exception:
                        user_role_ids = []

                # Get role details
                roles = []
                if user_role_ids:
                    placeholders = ','.join(['%s'] * len(user_role_ids))
                    cursor.execute(f"SELECT * FROM velocity.roles WHERE rid IN ({placeholders})", user_role_ids)
                    roles = cursor.fetchall()

                cursor.close()
                conn.close()

                return JsonResponse({'status': 'success', 'role_ids': user_role_ids, 'roles': roles}, status=200)
                
            except Exception as e:
                return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)

def setup(request):
    print(pylims.term(),pylims.info('building module list'))
    context={}
    #get all available modules 
    context['modules'] = pylims.build_module_dict()
    context['setup']=pylims.get_setup_options()
    context['links']=pylims.build_module_links(request)
    # print(context['modules'])
    return render(request, 'setup.html', context)

def setup_save(request):
    response={}
    response_code = handlePost(request)
    if response_code==400:
        response_data = {'error': 'Invalid JSON data', 'message': 'JSON decode error'}
        return JsonResponse(response_data, status=400)
    elif response_code==405:
        response_data = {'error': 'Invalid request method', 'message': 'Method not allowed'}
        return JsonResponse(response_data, status=405)
    json_data = json.loads(request.body)
    # print(json_data)
    
    file_path = settings.BASE_DIR / 'json/module_setup.json'
    with open(file_path, 'w+') as json_file:
        json.dump(json_data, json_file, indent=4)
    file_path = settings.BASE_DIR / 'setup_updated.py'
    current_datetime = datetime.datetime.now()
    formatted_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')
    with open(file_path, 'w+') as setupfile:
        setupfile.write(f'updated_datetime = "{formatted_datetime}"\n')
        
    response['msg_success']='Setup saved'
    response['status']='success';
    return JsonResponse(response)
    
def login_password_reset(request):
    return render(request, 'index.html')


def test(test):
    return test

@login_required
def get_all_users(request):
    """
    Get all users for the user role assignment interface.
    """
    if request.method == 'POST':
        try:
            conn = psycopg.connect(
                dbname=pylims.dbname,
                user=pylims.dbuser,
                password=pylims.dbpass,
                host=pylims.dbhost,
                port=pylims.dbport,
                row_factory=dict_row
            )
            cursor = conn.cursor()

            # Get all users from accounts table
            cursor.execute("SELECT userid, username, email FROM velocity.accounts ORDER BY email")
            users = cursor.fetchall()

            cursor.close()
            conn.close()

            return JsonResponse({'status': 'success', 'users': users}, status=200)
            
        except Exception as e:
            return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def get_all_roles(request):
    """
    Get all roles for the user role assignment interface.
    """
    if request.method == 'POST':
        try:
            conn = psycopg.connect(
                dbname=pylims.dbname,
                user=pylims.dbuser,
                password=pylims.dbpass,
                host=pylims.dbhost,
                port=pylims.dbport,
                row_factory=dict_row
            )
            cursor = conn.cursor()

            # Get all roles
            cursor.execute("SELECT * FROM velocity.roles ORDER BY role_name")
            roles = cursor.fetchall()
            
            # Get all permissions to resolve IDs to names
            cursor.execute("SELECT pid, permission FROM velocity.permissions")
            permissions_lookup = {row['pid']: row['permission'] for row in cursor.fetchall()}

            # Resolve permission IDs to names for each role
            for role in roles:
                if role['permission_set']:
                    # Parse permission set (could be JSON string or already parsed)
                    if isinstance(role['permission_set'], str):
                        try:
                            permission_ids = json.loads(role['permission_set'])
                        except:
                            permission_ids = []
                    else:
                        permission_ids = role['permission_set'] or []
                    
                    # Convert permission IDs to permission names
                    role['permission_names'] = [permissions_lookup.get(pid, f"Unknown permission {pid}") for pid in permission_ids]
                else:
                    role['permission_names'] = []

            cursor.close()
            conn.close()

            return JsonResponse({'status': 'success', 'roles': roles}, status=200)
            
        except Exception as e:
            return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def create_account(request):
    """
    Create a new user account with assigned roles and generate login code.
    
    Expected data:
    {
        "full_name": "John Doe",
        "username": "johndoe", 
        "email": "john@example.com",
        "role_ids": [1, 2, 3]
    }
    """
    print("=== CREATE ACCOUNT DEBUG START ===")
    print(f"Request method: {request.method}")
    print(f"Request headers: {dict(request.headers)}")
    print(f"Request body: {request.body}")
    
    if request.method == 'POST':
        try:
            print("Attempting to parse JSON data...")
            data = json.loads(request.body)
            print(f"Parsed data: {data}")
            
            full_name = data.get('full_name', '').strip()
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            role_ids = data.get('role_ids', [])
            
            print(f"Extracted values:")
            print(f"- full_name: '{full_name}'")
            print(f"- username: '{username}'")
            print(f"- email: '{email}'")
            print(f"- role_ids: {role_ids}")

            # Validate required fields
            if not full_name:
                print("ERROR: Full name is required")
                return JsonResponse({'error': 'Full name is required'}, status=400)
            
            if not username:
                print("ERROR: Username is required")
                return JsonResponse({'error': 'Username is required'}, status=400)
            
            if not email:
                print("ERROR: Email is required")
                return JsonResponse({'error': 'Email is required'}, status=400)

            print("Validation passed, attempting database connection...")
            
            try:
                conn = psycopg.connect(
                    host=settings.DATABASES['default']['HOST'],
                    port=settings.DATABASES['default']['PORT'],
                    dbname=settings.DATABASES['default']['NAME'],
                    user=settings.DATABASES['default']['USER'],
                    password=settings.DATABASES['default']['PASSWORD'],
                    row_factory=dict_row
                )
                cursor = conn.cursor()
                print("Database connection successful")

                # Check if username or email already exists
                print("Checking for existing users...")
                cursor.execute("SELECT userid FROM velocity.accounts WHERE username = %s OR email = %s", (username, email))
                existing_user = cursor.fetchone()
                if existing_user:
                    print(f"ERROR: User already exists with userid: {existing_user['userid']}")
                    return JsonResponse({'error': 'Username or email already exists'}, status=400)

                print("No existing users found, generating login code...")
                # Generate random login code
                import random
                import string
                login_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                print(f"Generated login code: {login_code}")

                # Create user account - match exact table structure
                print("Creating user account...")
                roles_json = json.dumps(role_ids) if role_ids else '[]'
                print(f"Roles JSON: {roles_json}")
                
                cursor.execute("""
                    INSERT INTO velocity.accounts (full_name, username, email, roles, activated, activation_code)
                    VALUES (%s, %s, %s, %s, FALSE, %s)
                    RETURNING userid
                """, (full_name, username, email, roles_json, login_code))
                
                result = cursor.fetchone()
                user_id = result['userid']
                print(f"User created with ID: {user_id}")

                # Send login email
                print("Attempting to send login email...")
                try:
                    send_login_email(full_name, email, login_code)
                    email_status = "sent successfully"
                    print("Email sent successfully")
                except Exception as email_error:
                    print(f"Warning: Failed to send email: {email_error}")
                    email_status = "failed to send"

                conn.commit()
                cursor.close()
                conn.close()
                print("Database transaction committed")

                response_data = {
                    'status': 'success', 
                    'user_id': user_id,
                    'login_code': login_code,
                    'email_status': email_status,
                    'role_ids': role_ids,
                    'message': f'Account created for {full_name} with {len(role_ids)} roles assigned'
                }
                print(f"Returning success response: {response_data}")
                return JsonResponse(response_data, status=200)
                
            except Exception as e:
                print(f"Database error: {str(e)}")
                print(f"Exception type: {type(e)}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)
                
        except json.JSONDecodeError as json_error:
            print(f"JSON decode error: {json_error}")
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as general_error:
            print(f"General error: {general_error}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return JsonResponse({'error': f'Server error: {str(general_error)}'}, status=500)
    else:
        print(f"ERROR: Invalid method {request.method}")
        return JsonResponse({'error': 'Method not allowed'}, status=405)

def send_login_email(full_name, email, login_code):
    """
    Send the login email using the system mail command.
    """
    login_link = f"{settings.SERVER_URL}/login/{login_code}"

    # Compose email content
    email_body = f"Dear {full_name},\n\nYour Velocity LIMS account has been created!\n\nClick the link below to activate your account:\n{login_link}\n\nAlternatively, you can login manually at {settings.SERVER_URL}/login with code: {login_code}\n\nWelcome to Velocity LIMS!\n\nBest regards,\nThe Velocity LIMS Team"

    # Prepare mail command
    subject = "Activate your Velocity LIMS Account"
    from_address = "Velocity LIMS <noreply@velocitylims.com>"
    
    # Use subprocess to send email via mail command
    try:
        # Create the mail command
        mail_cmd = [
            'mail',
            '-a', f'From: {from_address}',
            '-s', subject,
            email
        ]
        
        # Send email using subprocess
        process = subprocess.run(
            mail_cmd,
            input=email_body,
            text=True,
            capture_output=True,
            check=True
        )
        
        print(f"Email sent successfully to {email}")
        print(f"Subject: {subject}")
        print(f"Login code: {login_code}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Failed to send email: {e}")
        print(f"Error output: {e.stderr}")
        raise Exception(f"Mail command failed: {e}")
    except Exception as e:
        print(f"Email sending error: {e}")
        raise

def login_with_code(request, code):
    """
    Handle login via email verification code.
    
    Args:
        request: Django HttpRequest object
        code: The login code from the URL
        
    Returns:
        HttpResponse: Redirect to home if successful, login page if failed
    """
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
        
        # Look up user by activation code
        cursor.execute("""
            SELECT userid, email, username, full_name, roles, activation_code 
            FROM velocity.accounts 
            WHERE activated = FALSE AND activation_code = %s
        """, (code,))
        
        user = cursor.fetchone()
        
        if user:
            # Set session variables
            request.session['userid'] = user['userid']
            request.session['email'] = user['email']
            request.session['username'] = user['username']
            request.session['full_name'] = user['full_name']
            
            # Load user permissions (reuse existing logic from scripts/login.py)
            from scripts.login import load_user_permissions
            load_user_permissions(request, user['userid'])
            
            # Clear the activation code and set account as activated
            cursor.execute("""
                UPDATE velocity.accounts 
                SET activation_code = NULL, activated = TRUE 
                WHERE userid = %s
            """, (user['userid'],))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"User {user['username']} logged in via email verification and account activated")
            return redirect('home')
        else:
            cursor.close()
            conn.close()
            
            # Invalid or expired code
            print(f"Invalid login code attempted: {code}")
            return redirect('show_login')
            
    except Exception as e:
        print(f"Error during code-based login: {e}")
        return redirect('show_login')