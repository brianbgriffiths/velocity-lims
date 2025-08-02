"""
Assays management for Velocity LIMS
Handles creation, editing, and management of assays
"""

import json
import psycopg
from psycopg.rows import dict_row
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from settings.views import login_required, context_init, has_permission
import pylims


@login_required

def settings_assays(request):
    """
    Display the assays settings page with list of all assays
    Also handles POST requests for archive actions
    """
    # Handle POST requests (archive/unarchive actions and view loading)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'load_view':
                # Handle view loading
                view = data.get('view', 'active')
                
                conn = psycopg.connect(
                    dbname=pylims.dbname, 
                    user=pylims.dbuser, 
                    password=pylims.dbpass, 
                    host=pylims.dbhost, 
                    port=pylims.dbport, 
                    row_factory=dict_row
                )
                cursor = conn.cursor()
                
                # Build query based on view
                if view == 'active':
                    where_clause = "WHERE a.visible = true AND a.archived = false"
                elif view == 'archived':
                    where_clause = "WHERE a.visible = true AND a.archived = true"
                elif view == 'all_data':
                    # Load everything for client-side filtering (both archived and non-archived, but only visible)
                    where_clause = "WHERE a.visible = true"
                else:  # 'all' - visible but non-archived only
                    where_clause = "WHERE a.visible = true AND a.archived = false"
                
                cursor.execute(f"""
                    SELECT a.assayid, a.assay_name, a.modified, a.active_version, a.archived, a.visible,
                           av.version_name, av.version_major, av.version_minor, av.version_patch,
                           av.status, av.created as version_created,
                           dv.version_name as draft_version_name, dv.version_major as draft_major, 
                           dv.version_minor as draft_minor, dv.version_patch as draft_patch, dv.status as draft_status
                    FROM velocity.assay a
                    LEFT JOIN velocity.assay_versions av ON a.active_version = av.avid
                    LEFT JOIN velocity.assay_versions dv ON a.assayid = dv.assay AND dv.status IN (1, 2, 3)
                    {where_clause}
                    ORDER BY a.assay_name
                """)
                
                assays = cursor.fetchall()
                conn.close()
                
                return JsonResponse({
                    'status': 'success',
                    'assays': assays
                })
            
            elif action in ['archive', 'unarchive']:
                # Check permissions for archive/unarchive actions
                if not (has_permission(request, 'super_user') or has_permission(request, 'assayconfig_edit')):
                    return JsonResponse({'error': 'Insufficient permissions'}, status=403)
                
                assay_id = data.get('assay_id')
                if not assay_id:
                    return JsonResponse({'error': 'Missing assay ID'}, status=400)
                
                conn = psycopg.connect(
                    dbname=pylims.dbname, 
                    user=pylims.dbuser, 
                    password=pylims.dbpass, 
                    host=pylims.dbhost, 
                    port=pylims.dbport, 
                    row_factory=dict_row
                )
                cursor = conn.cursor()
                
                if action == 'archive':
                    # Archive assay by setting archived to true
                    cursor.execute("""
                        UPDATE velocity.assay 
                        SET archived = true, modified = CURRENT_TIMESTAMP
                        WHERE assayid = %s
                    """, (assay_id,))
                    message = 'Assay archived successfully'
                else:  # unarchive
                    # Unarchive assay by setting archived to false
                    cursor.execute("""
                        UPDATE velocity.assay 
                        SET archived = false, modified = CURRENT_TIMESTAMP
                        WHERE assayid = %s
                    """, (assay_id,))
                    message = 'Assay unarchived successfully'
                
                conn.commit()
                conn.close()
                
                return JsonResponse({
                    'status': 'success',
                    'message': message
                })
            else:
                return JsonResponse({'error': 'Invalid action'}, status=400)
                
        except Exception as e:
            return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)
    
    # Handle GET requests (display page)
    context = context_init(request)
    
    # Check if user has permission to view assays
    if not (has_permission(request, 'super_user') or 
            has_permission(request, 'assayconfig_view') or 
            has_permission(request, 'assayconfig_edit') or 
            has_permission(request, 'assayconfig_create')):
        return redirect('home')
    
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
        
        # Get all visible, non-archived assays with their active versions
        cursor.execute("""
            SELECT a.assayid, a.assay_name, a.modified, a.active_version, a.archived, a.visible,
                   av.version_name, av.version_major, av.version_minor, av.version_patch,
                   av.status, av.created as version_created
            FROM velocity.assay a
            LEFT JOIN velocity.assay_versions av ON a.active_version = av.avid
            WHERE a.visible = true AND a.archived = false
            ORDER BY a.assay_name
        """)
        
        context['assays'] = cursor.fetchall()
        
        # Get all versions for the dropdown (only for visible, non-archived assays)
        cursor.execute("""
            SELECT av.avid, av.version_name, av.assay, av.version_major, av.version_minor, av.version_patch,
                   a.assay_name
            FROM velocity.assay_versions av
            JOIN velocity.assay a ON av.assay = a.assayid
            WHERE a.visible = true AND a.archived = false
            ORDER BY a.assay_name, av.version_major DESC, av.version_minor DESC, av.version_patch DESC
        """)
        
        context['assay_versions'] = cursor.fetchall()
        
        conn.close()
        
    except Exception as e:
        context['assays'] = []
        context['assay_versions'] = []
        context['error'] = f"Database error: {str(e)}"
    
    return render(request, 'settings_assays.html', context)


@login_required

def create_assay(request):
    """
    Create a new assay with initial version
    This function is specifically for creating new assays and can be expanded later
    """
    print(f"create_assay called with method: {request.method}")
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    # Check permissions
    if not (has_permission(request, 'super_user') or has_permission(request, 'assayconfig_create')):
        print("Permission check failed")
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        print(f"Request body: {request.body}")
        data = json.loads(request.body)
        print(f"Parsed data: {data}")
        
        assay_name = data.get('assay_name', '').strip()
        create_initial_version = data.get('create_initial_version', True)  # Default to True for new assays
        
        print(f"Assay name: '{assay_name}', create_initial_version: {create_initial_version}")
        
        if not assay_name:
            return JsonResponse({'error': 'Assay name is required'}, status=400)
        
        print("Attempting database connection...")
        conn = psycopg.connect(
            dbname=pylims.dbname, 
            user=pylims.dbuser, 
            password=pylims.dbpass, 
            host=pylims.dbhost, 
            port=pylims.dbport, 
            row_factory=dict_row
        )
        print("Database connection successful")
        cursor = conn.cursor()
        
        print("Checking for existing assay...")
        # Check if assay name already exists
        cursor.execute("""
            SELECT assayid FROM velocity.assay 
            WHERE LOWER(assay_name) = LOWER(%s) AND visible = true
        """, (assay_name,))
        
        existing = cursor.fetchone()
        print(f"Existing assay check result: {existing}")
        
        if existing:
            return JsonResponse({'error': 'An assay with this name already exists'}, status=400)
        
        print("Creating new assay...")
        # Create new assay with default values
        cursor.execute("""
            INSERT INTO velocity.assay (assay_name, active_version, archived, visible)
            VALUES (%s, %s, %s, %s)
            RETURNING assayid, assay_name, modified, active_version, archived, visible
        """, (assay_name, None, False, True))  # Start with no active version, not archived, visible
        
        result = cursor.fetchone()
        print(f"New assay created: {result}")
        new_assayid = result['assayid']
        
        # Create initial version if requested
        if create_initial_version:
            version_name = f"{assay_name} init"
            cursor.execute("""
                INSERT INTO velocity.assay_versions 
                (assay, version_name, version_major, version_minor, version_patch, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING avid, version_name, version_major, version_minor, version_patch
            """, (new_assayid, version_name, 1, 0, 0, 1))  # status = 1 (draft)
            
            version_result = cursor.fetchone()
            new_avid = version_result['avid']
            
            # Do not automatically set as active version - new versions start as drafts
            message = f'Assay "{assay_name}" created successfully with initial draft version 1.0'
        else:
            message = f'Assay "{assay_name}" created successfully'
        
        conn.commit()
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'assay': result,
            'message': message
        })
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return JsonResponse({'error': f'Invalid JSON data: {str(e)}'}, status=400)
    except psycopg.Error as e:
        print(f"Database error: {e}")
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)
    except Exception as e:
        print(f"General error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@login_required

def create_draft_version(request):
    """
    Create a new draft version for an existing assay
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    # Check permissions
    if not (has_permission(request, 'super_user') or has_permission(request, 'assayconfig_version')):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        data = json.loads(request.body)
        assay_id = data.get('assay_id')
        
        if not assay_id:
            return JsonResponse({'error': 'Assay ID is required'}, status=400)
        
        conn = psycopg.connect(
            dbname=pylims.dbname, 
            user=pylims.dbuser, 
            password=pylims.dbpass, 
            host=pylims.dbhost, 
            port=pylims.dbport, 
            row_factory=dict_row
        )
        cursor = conn.cursor()
        
        # Check if assay exists
        cursor.execute("""
            SELECT assayid, assay_name FROM velocity.assay 
            WHERE assayid = %s AND visible = true
        """, (assay_id,))
        
        assay = cursor.fetchone()
        if not assay:
            return JsonResponse({'error': 'Assay not found'}, status=404)
        
        # Check if a draft/testing/locked version already exists (statuses 1, 2, 3)
        cursor.execute("""
            SELECT avid, status FROM velocity.assay_versions 
            WHERE assay = %s AND status IN (1, 2, 3)
        """, (assay_id,))
        
        existing_draft = cursor.fetchone()
        if existing_draft:
            status_names = {1: 'draft', 2: 'testing', 3: 'locked'}
            status_name = status_names.get(existing_draft['status'], 'development')
            return JsonResponse({'error': f'A {status_name} version already exists for this assay'}, status=400)
        
        # Get the latest version number to increment
        cursor.execute("""
            SELECT version_major, version_minor, version_patch 
            FROM velocity.assay_versions 
            WHERE assay = %s 
            ORDER BY version_major DESC, version_minor DESC, version_patch DESC 
            LIMIT 1
        """, (assay_id,))
        
        latest_version = cursor.fetchone()
        if latest_version:
            new_major = latest_version['version_major']
            new_minor = latest_version['version_minor'] + 1
            new_patch = 0
        else:
            new_major = 1
            new_minor = 0
            new_patch = 0
        
        # Create draft version
        version_name = f"{assay['assay_name']} v{new_major}.{new_minor} draft"
        cursor.execute("""
            INSERT INTO velocity.assay_versions 
            (assay, version_name, version_major, version_minor, version_patch, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING avid, version_name, version_major, version_minor, version_patch
        """, (assay_id, version_name, new_major, new_minor, new_patch, 1))  # status = 1 (draft)
        
        result = cursor.fetchone()
        conn.commit()
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'draft_version': result,
            'message': f'Draft version {new_major}.{new_minor} created successfully'
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Invalid JSON data: {str(e)}'}, status=400)
    except psycopg.Error as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@login_required
def settings_assay_view(request, assay_id):
    """
    View page for active assay version
    """
    # Check permissions
    if not (has_permission(request, 'super_user') or has_permission(request, 'assayconfig_view')):
        return redirect('home')
    
    # TODO: Implement assay view page
    # For now, just return a placeholder
    return render(request, 'assay_view_placeholder.html', {
        'assay_id': assay_id,
        'page_title': f'Assay View - ID {assay_id}'
    })


@login_required

def save_assay(request):
    """
    Update an existing assay (editing only, not creation)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    # Check permissions
    if not (has_permission(request, 'super_user') or has_permission(request, 'assayconfig_edit')):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        data = json.loads(request.body)
        assay_name = data.get('assay_name', '').strip()
        active_version = data.get('active_version')
        assayid = data.get('assayid')
        
        if not assay_name:
            return JsonResponse({'error': 'Assay name is required'}, status=400)
        
        if not assayid:
            return JsonResponse({'error': 'Assay ID is required for updates'}, status=400)
        
        conn = psycopg.connect(
            dbname=pylims.dbname, 
            user=pylims.dbuser, 
            password=pylims.dbpass, 
            host=pylims.dbhost, 
            port=pylims.dbport, 
            row_factory=dict_row
        )
        cursor = conn.cursor()
        
        # Update existing assay
        cursor.execute("""
            UPDATE velocity.assay 
            SET assay_name = %s, active_version = %s, modified = CURRENT_TIMESTAMP
            WHERE assayid = %s
            RETURNING assayid, assay_name, modified, active_version
        """, (assay_name, active_version, assayid))
        
        result = cursor.fetchone()
        if not result:
            return JsonResponse({'error': 'Assay not found'}, status=404)
        
        conn.commit()
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'assay': result,
            'message': f'Assay "{assay_name}" updated successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)


@login_required

def get_assay_details(request):
    """
    Get detailed information about a specific assay
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    # Check permissions
    if not (has_permission(request, 'super_user') or 
            has_permission(request, 'assayconfig_view') or 
            has_permission(request, 'assayconfig_edit') or 
            has_permission(request, 'assayconfig_create')):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        data = json.loads(request.body)
        assayid = data.get('assayid')
        
        if not assayid:
            return JsonResponse({'error': 'Assay ID is required'}, status=400)
        
        conn = psycopg.connect(
            dbname=pylims.dbname, 
            user=pylims.dbuser, 
            password=pylims.dbpass, 
            host=pylims.dbhost, 
            port=pylims.dbport, 
            row_factory=dict_row
        )
        cursor = conn.cursor()
        
        # Get assay details
        cursor.execute("""
            SELECT a.assayid, a.assay_name, a.modified, a.active_version,
                   av.version_name, av.version_major, av.version_minor, av.version_patch
            FROM velocity.assay a
            LEFT JOIN velocity.assay_versions av ON a.active_version = av.avid
            WHERE a.assayid = %s
        """, (assayid,))
        
        assay = cursor.fetchone()
        
        if not assay:
            return JsonResponse({'error': 'Assay not found'}, status=404)
        
        # Get specimen count for this assay
        cursor.execute("""
            SELECT COUNT(*) as specimen_count
            FROM velocity.specimens
            WHERE assayid = %s
        """, (assayid,))
        
        specimen_count = cursor.fetchone()['specimen_count']
        assay['specimen_count'] = specimen_count
        
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'assay': assay
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)


@login_required
def archive_assay(request):
    """
    Archive an assay by setting archived = true
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    # Check permissions
    if not (has_permission(request, 'super_user') or has_permission(request, 'assayconfig_edit')):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        data = json.loads(request.body)
        assay_id = data.get('assay_id')
        
        if not assay_id:
            return JsonResponse({'error': 'Assay ID is required'}, status=400)
        
        conn = psycopg.connect(
            dbname=pylims.dbname, 
            user=pylims.dbuser, 
            password=pylims.dbpass, 
            host=pylims.dbhost, 
            port=pylims.dbport, 
            row_factory=dict_row
        )
        cursor = conn.cursor()
        
        # Archive assay by setting archived to true
        cursor.execute("""
            UPDATE velocity.assay 
            SET archived = true, modified = CURRENT_TIMESTAMP
            WHERE assayid = %s
            RETURNING assayid, assay_name
        """, (assay_id,))
        
        result = cursor.fetchone()
        if not result:
            return JsonResponse({'error': 'Assay not found'}, status=404)
        
        conn.commit()
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Assay "{result["assay_name"]}" archived successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)


@login_required
def unarchive_assay(request):
    """
    Unarchive an assay by setting archived = false
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    # Check permissions
    if not (has_permission(request, 'super_user') or has_permission(request, 'assayconfig_edit')):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        data = json.loads(request.body)
        assay_id = data.get('assay_id')
        
        if not assay_id:
            return JsonResponse({'error': 'Assay ID is required'}, status=400)
        
        conn = psycopg.connect(
            dbname=pylims.dbname, 
            user=pylims.dbuser, 
            password=pylims.dbpass, 
            host=pylims.dbhost, 
            port=pylims.dbport, 
            row_factory=dict_row
        )
        cursor = conn.cursor()
        
        # Unarchive assay by setting archived to false
        cursor.execute("""
            UPDATE velocity.assay 
            SET archived = false, modified = CURRENT_TIMESTAMP
            WHERE assayid = %s
            RETURNING assayid, assay_name
        """, (assay_id,))
        
        result = cursor.fetchone()
        if not result:
            return JsonResponse({'error': 'Assay not found'}, status=404)
        
        conn.commit()
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Assay "{result["assay_name"]}" unarchived successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)


@login_required
def settings_assay_configure(request, assay_id):
    """
    Configure page for an assay version - shows steps and allows editing
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
        
        # Get the assay details and its current development version
        cursor.execute("""
            SELECT a.assayid, a.assay_name, a.modified, a.archived, a.visible,
                   av.avid, av.version_name, av.version_major, av.version_minor, av.version_patch,
                   av.status, av.created as version_created, av.modified as version_modified,
                   av.assay_steps
            FROM velocity.assay a
            LEFT JOIN velocity.assay_versions av ON a.assayid = av.assay AND av.status IN (1, 2, 3)
            WHERE a.assayid = %s AND a.visible = true
        """, (assay_id,))
        
        assay_data = cursor.fetchone()
        
        if not assay_data:
            conn.close()
            return render(request, 'settings_assays.html', {
                'error': 'Assay not found or no development version available'
            })
        
        # Get all steps for this assay version
        if assay_data['avid'] and assay_data.get('assay_steps'):
            # Extract step IDs from the assay_steps JSON field
            step_ids = assay_data['assay_steps']
            if step_ids:
                # Create placeholders for the IN clause
                placeholders = ','.join(['%s'] * len(step_ids))
                cursor.execute(f"""
                    SELECT scid, step_name, containers, controls, create_samples, 
                           pages, sample_data, step_scripts
                    FROM velocity.step_config
                    WHERE scid IN ({placeholders})
                """, step_ids)
                
                # Get the steps and maintain the order from assay_steps
                steps_dict = {row['scid']: row for row in cursor.fetchall()}
                steps = [steps_dict[step_id] for step_id in step_ids if step_id in steps_dict]
            else:
                steps = []
        else:
            steps = []
        
        conn.close()
        
        # Initialize context
        context = context_init(request)
        context.update({
            'assay': assay_data,
            'steps': steps,
            'has_steps': len(steps) > 0
        })
        
        return render(request, 'settings_assay_configure.html', context)
        
    except Exception as e:
        return render(request, 'settings_assays.html', {
            'error': f'Database error: {str(e)}'
        })


@login_required
def settings_assay_view(request, assay_id):
    """
    View page for an active assay version - read-only display
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
        
        # Get the assay details and its active version
        cursor.execute("""
            SELECT a.assayid, a.assay_name, a.modified, a.archived, a.visible,
                   av.avid, av.version_name, av.version_major, av.version_minor, av.version_patch,
                   av.status, av.created as version_created, av.modified as version_modified,
                   av.assay_steps
            FROM velocity.assay a
            LEFT JOIN velocity.assay_versions av ON a.active_version = av.avid
            WHERE a.assayid = %s AND a.visible = true
        """, (assay_id,))
        
        assay_data = cursor.fetchone()
        
        if not assay_data:
            conn.close()
            return render(request, 'settings_assays.html', {
                'error': 'Assay not found'
            })
        
        # Get all steps for this assay version
        if assay_data['avid'] and assay_data.get('assay_steps'):
            # Extract step IDs from the assay_steps JSON field
            step_ids = assay_data['assay_steps']
            if step_ids:
                # Create placeholders for the IN clause
                placeholders = ','.join(['%s'] * len(step_ids))
                cursor.execute(f"""
                    SELECT scid, step_name, containers, controls, create_samples, 
                           pages, sample_data, step_scripts
                    FROM velocity.step_config
                    WHERE scid IN ({placeholders})
                """, step_ids)
                
                # Get the steps and maintain the order from assay_steps
                steps_dict = {row['scid']: row for row in cursor.fetchall()}
                steps = [steps_dict[step_id] for step_id in step_ids if step_id in steps_dict]
            else:
                steps = []
        else:
            steps = []
        
        conn.close()
        
        # Initialize context
        context = context_init(request)
        context.update({
            'assay': assay_data,
            'steps': steps,
            'has_steps': len(steps) > 0,
            'is_view_only': True
        })
        
        return render(request, 'settings_assay_view.html', context)
        
    except Exception as e:
        return render(request, 'settings_assays.html', {
            'error': f'Database error: {str(e)}'
        })


@login_required
def save_step_order(request):
    """
    Save the new order of steps in an assay version
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    # Check permissions
    if not (has_permission(request, 'super_user') or has_permission(request, 'assayconfig_edit')):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        data = json.loads(request.body)
        assay_id = data.get('assay_id')
        step_order = data.get('step_order')  # List of step IDs in new order
        
        if not assay_id:
            return JsonResponse({'error': 'Assay ID is required'}, status=400)
        
        if not step_order or not isinstance(step_order, list):
            return JsonResponse({'error': 'Step order must be a list of step IDs'}, status=400)
        
        conn = psycopg.connect(
            dbname=pylims.dbname, 
            user=pylims.dbuser, 
            password=pylims.dbpass, 
            host=pylims.dbhost, 
            port=pylims.dbport, 
            row_factory=dict_row
        )
        cursor = conn.cursor()
        
        # Get the development version for this assay
        cursor.execute("""
            SELECT avid, assay_steps, version_major, version_minor, version_patch 
            FROM velocity.assay_versions 
            WHERE assay = %s AND status IN (1, 2, 3)
            LIMIT 1
        """, (assay_id,))
        
        version_data = cursor.fetchone()
        
        if not version_data:
            return JsonResponse({'error': 'No development version found for this assay'}, status=404)
        
        # Get current order and compare with new order
        current_order = version_data.get('assay_steps', []) or []
        
        # Normalize both orders for comparison (ensure they're both lists of integers)
        current_order_normalized = [int(x) for x in current_order] if current_order else []
        new_order_normalized = [int(x) for x in step_order]
        
        # Check if the order actually changed
        if current_order_normalized == new_order_normalized:
            # No change, return current version info without updating
            return JsonResponse({
                'status': 'success',
                'message': 'Step order unchanged',
                'version_unchanged': True,
                'version': {
                    'version_major': version_data['version_major'],
                    'version_minor': version_data['version_minor'], 
                    'version_patch': version_data['version_patch'] or 0
                }
            })
        
        # Order changed, update database and increment patch version
        step_order_json = json.dumps(step_order)
        
        # Update the assay_steps JSON field with the new order and increment patch version
        cursor.execute("""
            UPDATE velocity.assay_versions 
            SET assay_steps = %s, 
                version_patch = COALESCE(version_patch, 0) + 1,
                modified = CURRENT_TIMESTAMP
            WHERE avid = %s
            RETURNING version_major, version_minor, version_patch
        """, (step_order_json, version_data['avid']))
        
        updated_version = cursor.fetchone()
        
        conn.commit()
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Step order updated successfully (v{updated_version["version_major"]}.{updated_version["version_minor"]}.{updated_version["version_patch"]})',
            'version': updated_version
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Invalid JSON data: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)


@login_required
def save_version_name(request):
    """
    Update the version name for an assay version
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    # Check permissions
    if not (has_permission(request, 'super_user') or has_permission(request, 'assayconfig_edit')):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        data = json.loads(request.body)
        avid = data.get('avid')
        version_name = data.get('version_name', '').strip()
        
        if not avid:
            return JsonResponse({'error': 'Version ID is required'}, status=400)
        
        if not version_name:
            return JsonResponse({'error': 'Version name is required'}, status=400)
        
        conn = psycopg.connect(
            dbname=pylims.dbname, 
            user=pylims.dbuser, 
            password=pylims.dbpass, 
            host=pylims.dbhost, 
            port=pylims.dbport, 
            row_factory=dict_row
        )
        cursor = conn.cursor()
        
        # Get current version info to check if name actually changed
        cursor.execute("""
            SELECT version_name, version_major, version_minor, version_patch
            FROM velocity.assay_versions 
            WHERE avid = %s
        """, (avid,))
        
        current_version = cursor.fetchone()
        if not current_version:
            return JsonResponse({'error': 'Version not found'}, status=404)
        
        # Check if the version name actually changed
        current_name = current_version.get('version_name', '').strip()
        if current_name == version_name:
            # No change, return current version info without updating
            return JsonResponse({
                'status': 'success',
                'message': 'Version name unchanged',
                'version_unchanged': True,
                'version': {
                    'version_major': current_version['version_major'],
                    'version_minor': current_version['version_minor'],
                    'version_patch': current_version['version_patch'] or 0
                }
            })
        
        # Name changed, update database and increment patch version
        cursor.execute("""
            UPDATE velocity.assay_versions 
            SET version_name = %s, 
                version_patch = COALESCE(version_patch, 0) + 1,
                modified = CURRENT_TIMESTAMP
            WHERE avid = %s
            RETURNING avid, version_name, version_major, version_minor, version_patch
        """, (version_name, avid))
        
        result = cursor.fetchone()
        
        conn.commit()
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'version': result,
            'message': f'Version name updated to "{version_name}" (v{result["version_major"]}.{result["version_minor"]}.{result["version_patch"]})'
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Invalid JSON data: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)


@login_required
def get_step_config(request):
    """
    Get step configuration details for a specific step
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    # Check permissions
    if not (has_permission(request, 'super_user') or has_permission(request, 'assayconfig_view')):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        data = json.loads(request.body)
        scid = data.get('scid')
        
        if not scid:
            return JsonResponse({'error': 'Step configuration ID (scid) is required'}, status=400)
        
        conn = psycopg.connect(
            dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, 
            host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row
        )
        cursor = conn.cursor()
        
        # Get step configuration details
        cursor.execute("""
            SELECT scid, step_name, containers, controls, create_samples, 
                   pages, sample_data, step_scripts
            FROM velocity.step_config
            WHERE scid = %s
        """, (scid,))
        
        step_config = cursor.fetchone()
        
        if not step_config:
            return JsonResponse({'error': 'Step configuration not found'}, status=404)
        
        # If there are containers configured, fetch their full details
        containers_with_details = []
        if step_config['containers']:
            try:
                container_ids = [c.get('cid') for c in step_config['containers'] if c.get('cid')]
                if container_ids:
                    # Create placeholders for the IN clause
                    placeholders = ','.join(['%s'] * len(container_ids))
                    cursor.execute(f"""
                        SELECT cid, type_name, rows, columns, well_type, border_type, color,
                               restricted_well_map, special_well_map, corner_types,
                               margin_width, well_padding
                        FROM velocity.container_config 
                        WHERE cid IN ({placeholders})
                        ORDER BY type_name
                    """, container_ids)
                    
                    available_containers = {c['cid']: c for c in cursor.fetchall()}
                    
                    # Maintain the order from the original containers list
                    for container_ref in step_config['containers']:
                        cid = container_ref.get('cid')
                        if cid and cid in available_containers:
                            containers_with_details.append(available_containers[cid])
            except Exception as e:
                print(f"Error fetching container details: {e}")
                # Fall back to original containers data if there's an error
                containers_with_details = step_config['containers']
        
        # Update step_config with detailed container information
        step_config['containers'] = containers_with_details
        
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'step_config': step_config
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Invalid JSON data: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)


@login_required
def save_step_config(request):
    """
    Save step configuration changes
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    # Check permissions
    if not (has_permission(request, 'super_user') or has_permission(request, 'assayconfig_edit')):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        data = json.loads(request.body)
        scid = data.get('scid')
        step_name = data.get('step_name', '').strip()
        containers = data.get('containers', [])
        controls = data.get('controls', [])
        create_samples = data.get('create_samples', 1)
        pages = data.get('pages', [])
        sample_data = data.get('sample_data', [])
        step_scripts = data.get('step_scripts', [])
        
        # Extract just the container IDs for storage (containers may contain full details)
        container_refs = []
        for container in containers:
            if isinstance(container, dict) and container.get('cid'):
                container_refs.append({'cid': container['cid']})
        
        if not scid:
            return JsonResponse({'error': 'Step configuration ID (scid) is required'}, status=400)
        
        if not step_name:
            return JsonResponse({'error': 'Step name is required'}, status=400)
        
        conn = psycopg.connect(
            dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, 
            host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row
        )
        cursor = conn.cursor()
        
        # First, get current step configuration to check for changes
        cursor.execute("""
            SELECT step_name, containers, controls, create_samples, 
                   pages, sample_data, step_scripts
            FROM velocity.step_config
            WHERE scid = %s
        """, (scid,))
        
        current_config = cursor.fetchone()
        
        if not current_config:
            return JsonResponse({'error': 'Step configuration not found'}, status=404)
        
        # Check if any values have actually changed
        current_containers = current_config.get('containers', []) or []
        current_controls = current_config.get('controls', []) or []
        current_pages = current_config.get('pages', []) or []
        current_sample_data = current_config.get('sample_data', []) or []
        current_step_scripts = current_config.get('step_scripts', []) or []
        
        # Compare all fields for changes
        config_unchanged = (
            current_config['step_name'] == step_name and
            current_config['create_samples'] == create_samples and
            current_containers == container_refs and
            current_controls == controls and
            current_pages == pages and
            current_sample_data == sample_data and
            current_step_scripts == step_scripts
        )
        
        if config_unchanged:
            conn.close()
            return JsonResponse({
                'status': 'success',
                'config_unchanged': True,
                'step_config': {
                    'scid': scid,
                    'step_name': step_name
                },
                'message': 'Step configuration unchanged'
            })
        
        # Update step configuration
        cursor.execute("""
            UPDATE velocity.step_config
            SET step_name = %s,
                containers = %s,
                controls = %s,
                create_samples = %s,
                pages = %s,
                sample_data = %s,
                step_scripts = %s
            WHERE scid = %s
            RETURNING scid, step_name
        """, (step_name, json.dumps(container_refs), json.dumps(controls), 
              create_samples, json.dumps(pages), json.dumps(sample_data), 
              json.dumps(step_scripts), scid))
        
        result = cursor.fetchone()
        
        if not result:
            return JsonResponse({'error': 'Step configuration not found'}, status=404)
        
        # Find which assay version contains this step and increment its patch version
        cursor.execute("""
            SELECT avid, assay_steps, version_major, version_minor, version_patch
            FROM velocity.assay_versions 
            WHERE JSON_EXTRACT_PATH_TEXT(assay_steps::text, '0') = %s 
               OR %s = ANY(SELECT CAST(value AS TEXT) FROM JSON_ARRAY_ELEMENTS_TEXT(assay_steps))
        """, (str(scid), str(scid)))
        
        version_data = cursor.fetchone()
        
        if version_data:
            # Increment patch version
            new_patch = (version_data['version_patch'] or 0) + 1
            
            cursor.execute("""
                UPDATE velocity.assay_versions 
                SET version_patch = %s,
                    modified = CURRENT_TIMESTAMP
                WHERE avid = %s
                RETURNING avid, version_major, version_minor, version_patch
            """, (new_patch, version_data['avid']))
            
            updated_version = cursor.fetchone()
        else:
            updated_version = None
        
        conn.commit()
        conn.close()
        
        response_data = {
            'status': 'success',
            'step_config': result,
            'message': f'Step configuration "{step_name}" updated successfully'
        }
        
        if updated_version:
            response_data['version'] = updated_version
            response_data['message'] += f' (v{updated_version["version_major"]}.{updated_version["version_minor"]}.{updated_version["version_patch"]})'
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Invalid JSON data: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)
