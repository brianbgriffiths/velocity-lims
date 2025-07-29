from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import subprocess
import random
import string
import pylims
import psycopg
from psycopg.rows import dict_row
from settings import settings
from settings.views import login_required, context_init


@login_required
def settings_roles(request):
    context = context_init(request)

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
