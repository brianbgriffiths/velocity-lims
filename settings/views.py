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

def context_init(request):
    context = {}
    context['userid'] = request.session.get('userid', None)
    context['full_name'] = request.session.get('full_name', None)
    context['permissions'] = get_user_permissions(request)
    return context

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
                        from scripts.roles import send_login_email
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
    context = context_init(request)
    return render(request, 'logout.html', context)

@login_required
def view_settings(request):
    context = context_init(request)
    return render(request, 'settings.html', context)

@login_required
def settings_operators(request):
    context = context_init(request)
    return render(request, 'settings_operators.html', context)

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
