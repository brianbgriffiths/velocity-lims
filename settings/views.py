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
        context['info'].append(['Pylims Version',file.read()])
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
        cursor = conn.cursor
        
        # Query to count total samples
        cursor.execute("SELECT COUNT(*) as total_samples FROM samples;")
        result = cursor.fetchone()
        
        # Also get count from velocity.specimens if it exists
        try:
            cursor.execute("SELECT COUNT(*) as total_specimens FROM velocity.specimens;")
            velocity_result = cursor.fetchone()
            context['info'].append(['Sample Count', velocity_result['total_specimens']])
        except:
            context['info'].append(['Sample Count', 0])

    except Exception as e:
        context['info'].append(['Sample Count', f'Error: {str(e)}'])

    if not is_user_logged_in(request):
        context['userid'] = None
    else:
        context['userid'] = request.session.get('userid', None)
    return render(request, 'index.html', context)

def show_login(request):
    context = {}
    return render(request, 'login.html', context)

@login_required
def show_logout(request):
    context = {}
    context['userid'] = request.session.get('userid', None)
    return render(request, 'logout.html', context)

@login_required
def view_settings(request):
    context = {}
    context['userid'] = request.session.get('userid', None)

    return render(request, 'settings.html', context)

@login_required
def settings_operators(request):
    context = {}
    context['userid'] = request.session.get('userid', None)

    return render(request, 'settings_operators.html', context)

@login_required
def settings_roles(request):
    context = {}
    context['userid'] = request.session.get('userid', None)

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
        context['permissions'] = permissions
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