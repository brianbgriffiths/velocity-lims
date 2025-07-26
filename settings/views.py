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
    return 'userid' in request.session and request.session['userid'] is not None

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

def get_sample_count(request):
    """
    Query to get the total count of samples in the database.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        JsonResponse: JSON response containing the sample count
    """
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
        
        # Query to count total samples
        cursor.execute("SELECT COUNT(*) as total_samples FROM samples;")
        result = cursor.fetchone()
        
        # Also get count from velocity.samples if it exists
        try:
            cursor.execute("SELECT COUNT(*) as velocity_samples FROM velocity.samples;")
            velocity_result = cursor.fetchone()
        except:
            velocity_result = {'velocity_samples': 0}
        
        cursor.close()
        conn.close()
        
        response = {
            'status': 'success',
            'total_samples': result['total_samples'],
            'velocity_samples': velocity_result['velocity_samples']
        }
        
        return JsonResponse(response)
        
    except Exception as e:
        response = {
            'status': 'error',
            'error': f'Database error: {str(e)}'
        }
        return JsonResponse(response, status=500)

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
        
        # Also get count from velocity.samples if it exists
        try:
            cursor.execute("SELECT COUNT(*) as velocity_samples FROM velocity.samples;")
            velocity_result = cursor.fetchone()
            context['info'].append(['Total Samples', velocity_result['velocity_samples']])
        except:
            pass  # velocity.samples table might not exist
        
        cursor.close()
        conn.close()
        
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