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


def archive_assay_version(cursor, avid):
    """
    Archive the current state of an assay version before updating it
    This copies the current version to the assay_versions_archive table
    """
    try:
        # Get the current version data
        cursor.execute("""
            SELECT version_name, version_major, version_minor, version_patch, 
                   modified, assay, assay_steps
            FROM velocity.assay_versions 
            WHERE avid = %s
        """, (avid,))
        
        current_version = cursor.fetchone()
        if not current_version:
            print(f"Warning: No version found with avid {avid} to archive")
            return False
        
        # Insert into archive table with all available data including original_avid
        cursor.execute("""
            INSERT INTO velocity.assay_versions_archive 
            (original_avid, version_name, version_major, version_minor, version_patch, 
             modified, assay, assay_steps)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING avaid
        """, (
            avid,  # Store the original avid
            current_version['version_name'],
            current_version['version_major'],
            current_version['version_minor'],
            current_version['version_patch'],
            current_version['modified'],
            current_version['assay'],
            json.dumps(current_version['assay_steps']) if current_version['assay_steps'] is not None else None
        ))
        
        archive_result = cursor.fetchone()
        archive_id = archive_result['avaid']
        
        print(f"Archived version {avid} to archive ID {archive_id}")
        return True
        
    except Exception as e:
        print(f"Error archiving version {avid}: {str(e)}")
        return False


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
def settings_assay_configure(request, assay_id, step_id=None):
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
                    SELECT scid, step_name, containers, special_samples, create_samples, 
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
        
        # Validate step_id if provided
        selected_step = None
        if step_id is not None:
            # Check if the provided step_id is valid for this assay
            selected_step = next((step for step in steps if step['scid'] == step_id), None)
            if not selected_step:
                # Step ID not found or not part of this assay, redirect to assay config without step
                return redirect('settings_assay_configure', assay_id=assay_id)
        
        # Get special sample types for the step configuration
        cursor.execute("""SELECT * FROM velocity.special_samples ss JOIN velocity.special_sample_types sst ON sst.sstid=ss.special_type;""")
        special_sample_types = cursor.fetchall()
        
        conn.close()
        
        # Initialize context
        context = context_init(request)
        context.update({
            'assay': assay_data,
            'steps': steps,
            'has_steps': len(steps) > 0,
            'special_sample_types_json': json.dumps(special_sample_types),
            'selected_step_id': step_id,
            'selected_step': selected_step
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
                    SELECT scid, step_name, containers, special_samples, create_samples, 
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
        
        # Order changed, archive current version before updating
        archive_success = archive_assay_version(cursor, version_data['avid'])
        if not archive_success:
            print("Warning: Failed to archive version before updating, continuing anyway")
        
        # Update database and increment patch version
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
        
        # Name changed, archive current version before updating
        archive_success = archive_assay_version(cursor, avid)
        if not archive_success:
            print("Warning: Failed to archive version before updating, continuing anyway")
        
        # Update database and increment patch version
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
            SELECT scid, step_name, containers, special_samples, create_samples, 
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
                # Parse containers JSON if it's a string
                containers_data = step_config['containers']
                if isinstance(containers_data, str):
                    containers_data = json.loads(containers_data)
                
                print(f"Containers data type: {type(containers_data)}")
                print(f"Containers data: {containers_data}")
                
                # Handle different formats:
                # New format: {enabled_ids: [1,2], configurations: {1: {config}}}
                # Legacy format: [1, 2, 3] or [{cid: 1}, {cid: 2}]
                
                if isinstance(containers_data, dict) and 'enabled_ids' in containers_data:
                    # New format
                    enabled_ids = containers_data.get('enabled_ids', [])
                    configurations = containers_data.get('configurations', {})
                    
                    if enabled_ids:
                        # Fetch container details from database
                        placeholders = ','.join(['%s'] * len(enabled_ids))
                        cursor.execute(f"""
                            SELECT cid, type_name, rows, columns, well_type, border_type, color,
                                   restricted_well_map, special_well_map, corner_types,
                                   margin_width, well_padding
                            FROM velocity.container_config 
                            WHERE cid IN ({placeholders})
                            ORDER BY type_name
                        """, enabled_ids)
                        
                        available_containers = {c['cid']: c for c in cursor.fetchall()}
                        
                        # Build containers with their configurations
                        for container_id in enabled_ids:
                            if container_id in available_containers:
                                container = available_containers[container_id].copy()
                                if str(container_id) in configurations:
                                    container['config'] = configurations[str(container_id)]
                                elif container_id in configurations:
                                    container['config'] = configurations[container_id]
                                containers_with_details.append(container)
                
                else:
                    # Legacy format handling
                    container_ids = []
                    container_configs = {}
                    
                    if isinstance(containers_data, list):
                        for c in containers_data:
                            if isinstance(c, dict) and c.get('cid'):
                                container_ids.append(c['cid'])
                                if c.get('config'):
                                    container_configs[c['cid']] = c['config']
                            elif isinstance(c, (int, str)) and str(c).isdigit():
                                container_ids.append(int(c))
                    
                    if container_ids:
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
                        
                        for container_id in container_ids:
                            if container_id in available_containers:
                                container = available_containers[container_id].copy()
                                if container_id in container_configs:
                                    container['config'] = container_configs[container_id]
                                containers_with_details.append(container)
                        
                print(f"Final containers with details: {containers_with_details}")
            except Exception as e:
                print(f"Error fetching container details: {e}")
                # Fall back to original containers data if there's an error
                containers_with_details = step_config['containers']
        
        # Update step_config with detailed container information
        step_config['containers'] = containers_with_details
        
        # Load actual special samples data and organize by type
        special_samples_organized = {}
        if step_config['special_samples']:
            try:
                # Parse special_samples JSON if it's a string
                special_samples_data = step_config['special_samples']
                if isinstance(special_samples_data, str):
                    special_samples_data = json.loads(special_samples_data)
                
                print(f"Special samples data from step config: {special_samples_data}")
                
                # Handle new format: {enabled_ids: [...], configurations: {...}}
                if isinstance(special_samples_data, dict) and 'enabled_ids' in special_samples_data:
                    special_samples_ids = special_samples_data.get('enabled_ids', [])
                    configurations = special_samples_data.get('configurations', {})
                    print(f"New format - IDs: {special_samples_ids}, Configs: {configurations}")
                    
                    if special_samples_ids and len(special_samples_ids) > 0:
                        # Get the actual special samples data with their types
                        placeholders = ','.join(['%s'] * len(special_samples_ids))
                        cursor.execute(f"""
                            SELECT ss.*, sst.sstid as type_id, sst.special_type_name
                            FROM velocity.special_samples ss
                            JOIN velocity.special_sample_types sst ON ss.special_type = sst.sstid
                            WHERE ss.ssid IN ({placeholders}) AND ss.special_status = 2
                            ORDER BY sst.special_type_name, ss.special_name
                        """, special_samples_ids)
                        
                        special_samples_from_db = cursor.fetchall()
                        print(f"Loaded special samples from DB: {special_samples_from_db}")
                        
                        # For each sample, use the special_type from the configuration
                        for sample in special_samples_from_db:
                            sample_id = sample['ssid']
                            config = configurations.get(str(sample_id), configurations.get(sample_id, {}))
                            type_id = config.get('special_type', sample['type_id'])
                            
                            if type_id not in special_samples_organized:
                                special_samples_organized[type_id] = []
                            
                            # Add the configured type to the sample data
                            sample_with_config = sample.copy()
                            sample_with_config['special_type'] = type_id
                            special_samples_organized[type_id].append(sample_with_config)
                    
                    # Return the data in the new format for the frontend
                    step_config['special_samples'] = special_samples_data
                    
                # Handle legacy format: array of IDs
                elif isinstance(special_samples_data, list) and len(special_samples_data) > 0:
                    print("Legacy format - array of IDs")
                    # Get the actual special samples data with their types
                    placeholders = ','.join(['%s'] * len(special_samples_data))
                    cursor.execute(f"""
                        SELECT ss.*, sst.sstid as type_id, sst.special_type_name
                        FROM velocity.special_samples ss
                        JOIN velocity.special_sample_types sst ON ss.special_type = sst.sstid
                        WHERE ss.ssid IN ({placeholders}) AND ss.special_status = 2
                        ORDER BY sst.special_type_name, ss.special_name
                    """, special_samples_data)
                    
                    special_samples_from_db = cursor.fetchall()
                    print(f"Loaded special samples from DB: {special_samples_from_db}")
                    
                    # Organize by type ID (sstid)
                    for sample in special_samples_from_db:
                        type_id = sample['type_id']
                        if type_id not in special_samples_organized:
                            special_samples_organized[type_id] = []
                        special_samples_organized[type_id].append(sample)
                    
                    print(f"Organized special samples: {special_samples_organized}")
                    
                    # For legacy data, return the organized structure
                    step_config['special_samples'] = special_samples_organized
                        
            except Exception as e:
                print(f"Error loading special samples: {e}")
                special_samples_organized = {}
                # Return empty data on error
                step_config['special_samples'] = {}
        
        # Handle pages configuration - convert from array of ints to new object format
        pages_with_details = []
        if step_config['pages']:
            try:
                # Parse pages JSON if it's a string
                pages_data = step_config['pages']
                if isinstance(pages_data, str):
                    pages_data = json.loads(pages_data)
                
                print(f"Pages data type: {type(pages_data)}")
                print(f"Pages data: {pages_data}")
                
                # Handle different formats:
                # New format: {enabled_ids: [1,2], configurations: {1: {config}}}
                # Legacy format: [1, 2, 3]
                
                if isinstance(pages_data, dict) and 'enabled_ids' in pages_data:
                    # New format
                    enabled_ids = pages_data.get('enabled_ids', [])
                    configurations = pages_data.get('configurations', {})
                    
                    if enabled_ids:
                        # Fetch page details from database
                        placeholders = ','.join(['%s'] * len(enabled_ids))
                        cursor.execute(f"""
                            SELECT pcid, page as page_name, show_after_complete
                            FROM velocity.page_config 
                            WHERE pcid IN ({placeholders})
                            ORDER BY page_name
                        """, enabled_ids)
                        
                        available_pages = {p['pcid']: p for p in cursor.fetchall()}
                        
                        # Build pages with their configurations
                        for page_id in enabled_ids:
                            if page_id in available_pages:
                                page = available_pages[page_id].copy()
                                if str(page_id) in configurations:
                                    page['config'] = configurations[str(page_id)]
                                elif page_id in configurations:
                                    page['config'] = configurations[page_id]
                                pages_with_details.append(page)
                
                else:
                    # Legacy format handling - array of IDs
                    page_ids = []
                    page_configs = {}
                    
                    if isinstance(pages_data, list):
                        for p in pages_data:
                            if isinstance(p, dict) and p.get('pcid'):
                                page_ids.append(p['pcid'])
                                if p.get('config'):
                                    page_configs[p['pcid']] = p['config']
                            elif isinstance(p, (int, str)) and str(p).isdigit():
                                page_ids.append(int(p))
                    
                    if page_ids:
                        placeholders = ','.join(['%s'] * len(page_ids))
                        cursor.execute(f"""
                            SELECT pcid, page as page_name, show_after_complete
                            FROM velocity.page_config 
                            WHERE pcid IN ({placeholders})
                            ORDER BY page_name
                        """, page_ids)
                        
                        available_pages = {p['pcid']: p for p in cursor.fetchall()}
                        
                        for page_id in page_ids:
                            if page_id in available_pages:
                                page = available_pages[page_id].copy()
                                if page_id in page_configs:
                                    page['config'] = page_configs[page_id]
                                pages_with_details.append(page)
                        
                print(f"Final pages with details: {pages_with_details}")
            except Exception as e:
                print(f"Error fetching page details: {e}")
                # Fall back to original pages data if there's an error
                pages_with_details = step_config['pages']
        
        # Update step_config with detailed page information
        step_config['pages'] = pages_with_details
        
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
        special_samples_data = data.get('special_samples', {})  # New format: {enabled_ids: [...], configurations: {...}}
        create_samples = data.get('create_samples', 1)
        pages_data = data.get('pages', {})  # New format: {enabled_ids: [...], configurations: {...}}
        sample_data = data.get('sample_data', [])
        step_scripts = data.get('step_scripts', [])
        
        # containers now contains enabled IDs and configurations
        # Format: {enabled_ids: [1,2,3], configurations: {1: {config}, 2: {config}}}
        containers_data = data.get('containers', {})
        enabled_containers = containers_data.get('enabled_ids', [])
        container_configs = containers_data.get('configurations', {})
        
        print(f"Received containers_data: {containers_data}")
        print(f"Enabled containers: {enabled_containers}")
        print(f"Container configs: {container_configs}")
        
        # Handle special samples in new format
        print(f"Received special_samples_data: {special_samples_data}")
        
        # Handle pages in new format
        print(f"Received pages_data: {pages_data}")
        
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
            SELECT step_name, containers, special_samples, create_samples, 
                   pages, sample_data, step_scripts
            FROM velocity.step_config
            WHERE scid = %s
        """, (scid,))
        
        current_config = cursor.fetchone()
        
        if not current_config:
            return JsonResponse({'error': 'Step configuration not found'}, status=404)
        
        # Check if any values have actually changed
        current_containers_data = current_config.get('containers', {}) or {}
        current_enabled_containers = current_containers_data.get('enabled_ids', []) if isinstance(current_containers_data, dict) else current_containers_data
        current_container_configs = current_containers_data.get('configurations', {}) if isinstance(current_containers_data, dict) else {}
        
        print(f"Current containers data from DB: {current_containers_data}")
        print(f"Current enabled containers: {current_enabled_containers}")
        print(f"Current container configs: {current_container_configs}")
        print(f"New enabled containers: {enabled_containers}")
        print(f"New container configs: {container_configs}")
        
        # Handle current special samples data (could be old or new format)
        current_special_samples_raw = current_config.get('special_samples', {}) or {}
        current_pages_raw = current_config.get('pages', {}) or {}
        current_sample_data = current_config.get('sample_data', []) or []
        current_step_scripts = current_config.get('step_scripts', []) or []
        
        # Compare all fields for changes
        containers_changed = (current_enabled_containers != enabled_containers or current_container_configs != container_configs)
        special_samples_changed = (current_special_samples_raw != special_samples_data)
        pages_changed = (current_pages_raw != pages_data)
        
        config_unchanged = (
            current_config['step_name'] == step_name and
            current_config['create_samples'] == create_samples and
            not containers_changed and
            not special_samples_changed and
            not pages_changed and
            current_sample_data == sample_data and
            current_step_scripts == step_scripts
        )
        
        print(f"Containers changed: {containers_changed}")
        print(f"Special samples changed: {special_samples_changed}")
        print(f"Pages changed: {pages_changed}")
        print(f"Config unchanged: {config_unchanged}")
        
        if config_unchanged:
            print("Configuration unchanged, returning early")
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
        
        print("Configuration changed, proceeding with update")
        
        # Update step configuration
        try:
            cursor.execute("""
                UPDATE velocity.step_config
                SET step_name = %s,
                    containers = %s,
                    special_samples = %s,
                    create_samples = %s,
                    pages = %s,
                    sample_data = %s,
                    step_scripts = %s
                WHERE scid = %s
                RETURNING scid, step_name
            """, (step_name, json.dumps(containers_data), json.dumps(special_samples_data), 
                  create_samples, json.dumps(pages_data), json.dumps(sample_data), 
                  json.dumps(step_scripts), scid))
            
            result = cursor.fetchone()
            print(f"Database update result: {result}")
            
        except Exception as db_error:
            print(f"Database update error: {db_error}")
            print(f"Data being saved: containers={json.dumps(containers_data)}")
            conn.close()
            return JsonResponse({'error': f'Database update failed: {str(db_error)}'}, status=500)
        
        if not result:
            conn.close()
            return JsonResponse({'error': 'Step configuration not found'}, status=404)
        
        print(f"Step configuration updated successfully: {result}")
        
        # Find which assay version contains this step and increment its patch version
        try:
            print(f"Looking for assay version containing step {scid}")
            # First, let's see what's in the assay_versions table
            cursor.execute("""
                SELECT avid, assay_steps, version_major, version_minor, version_patch
                FROM velocity.assay_versions 
                ORDER BY avid
            """)
            
            all_versions = cursor.fetchall()
            print(f"All versions in database: {all_versions}")
            
            # Now try the original query
            cursor.execute("""
                SELECT avid, assay_steps, version_major, version_minor, version_patch
                FROM velocity.assay_versions 
                WHERE assay_steps::jsonb ? %s
            """, (str(scid),))
            
            version_data = cursor.fetchone()
            print(f"Found version data with JSONB ? query: {version_data}")
            
            # If that didn't work, try with @> operator for array containment
            if not version_data:
                print("Trying array containment query...")
                cursor.execute("""
                    SELECT avid, assay_steps, version_major, version_minor, version_patch
                    FROM velocity.assay_versions 
                    WHERE assay_steps::jsonb @> %s
                """, (json.dumps([scid]),))
                
                version_data = cursor.fetchone()
                print(f"Found version data with @> query: {version_data}")
            
        except Exception as version_error:
            print(f"Error finding version data: {version_error}")
            conn.close()
            return JsonResponse({'error': f'Error finding version data: {str(version_error)}'}, status=500)
        
        if version_data:
            # Archive current version before incrementing patch version
            archive_success = archive_assay_version(cursor, version_data['avid'])
            if not archive_success:
                print("Warning: Failed to archive version before updating, continuing anyway")
            
            # Increment patch version
            try:
                new_patch = (version_data['version_patch'] or 0) + 1
                print(f"Incrementing patch version to: {new_patch}")
                
                cursor.execute("""
                    UPDATE velocity.assay_versions 
                    SET version_patch = %s,
                        modified = CURRENT_TIMESTAMP
                    WHERE avid = %s
                    RETURNING avid, version_major, version_minor, version_patch
                """, (new_patch, version_data['avid']))
                
                updated_version = cursor.fetchone()
                print(f"Updated version: {updated_version}")
                
            except Exception as patch_error:
                print(f"Error updating patch version: {patch_error}")
                conn.close()
                return JsonResponse({'error': f'Error updating patch version: {str(patch_error)}'}, status=500)
        else:
            print("No version data found for this step")
            updated_version = None
        
        conn.commit()
        conn.close()
        
        print("Transaction committed successfully")
        
        # Prepare response
        response_data = {
            'status': 'success',
            'config_unchanged': False,
            'step_config': {
                'scid': result['scid'],
                'step_name': result['step_name']
            },
            'message': 'Step configuration saved successfully'
        }
        
        if updated_version:
            response_data['version'] = {
                'version_major': updated_version['version_major'],
                'version_minor': updated_version['version_minor'],
                'version_patch': updated_version['version_patch']
            }
        
        print(f"Sending response: {response_data}")
        return JsonResponse(response_data)
        
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Invalid JSON data: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)


@login_required
def get_special_samples(request):
    """
    Get special samples by type ID (sstid from special_sample_types table)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    # Check permissions
    if not (has_permission(request, 'super_user') or has_permission(request, 'assayconfig_view')):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        data = json.loads(request.body)
        special_type_id = data.get('special_type_id')  # This is now sstid from special_sample_types
        
        if not special_type_id:
            return JsonResponse({'error': 'special_type_id is required'}, status=400)
        
        conn = psycopg.connect(
            dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, 
            host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row
        )
        cursor = conn.cursor()
        
        # Get special samples by type ID, joining with special_sample_types
        # First check if any samples exist for this type (regardless of status)
        cursor.execute("""
            SELECT COUNT(*) as total_count
            FROM velocity.special_samples ss
            WHERE ss.special_type = %s
        """, (special_type_id,))
        
        total_count = cursor.fetchone()['total_count']
        print(f"DEBUG: Found {total_count} total special samples for type {special_type_id}")
        
        # Check active samples
        cursor.execute("""
            SELECT COUNT(*) as active_count
            FROM velocity.special_samples ss
            WHERE ss.special_type = %s AND ss.special_status = 1
        """, (special_type_id,))
        
        active_count = cursor.fetchone()['active_count']
        print(f"DEBUG: Found {active_count} active special samples for type {special_type_id}")
        
        # Get all samples for this type with status info
        cursor.execute("""
            SELECT ss.ssid, ss.special_name, ss.special_type, ss.part_number, ss.color, 
                   ss.custom_color, ss.custom_icon, ss.default_well, ss.default_index,
                   ss.special_status, sst.special_type_name
            FROM velocity.special_samples ss
            JOIN velocity.special_sample_types sst ON ss.special_type = sst.sstid
            WHERE ss.special_type = %s AND ss.special_status = 1
            ORDER BY ss.special_name
        """, (special_type_id,))
        
        special_samples = cursor.fetchall()
        print(f"DEBUG: Returning {len(special_samples)} special samples for type {special_type_id}")
        
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'special_samples': special_samples
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Invalid JSON data: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)




@login_required
def get_available_pages(request):
    """
    Get all available pages from page_config table
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    # Check permissions
    if not (has_permission(request, 'super_user') or has_permission(request, 'assayconfig_view')):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        conn = psycopg.connect(
            dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, 
            host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row
        )
        cursor = conn.cursor()
        
        # Get all available pages
        cursor.execute("""
            SELECT pcid, page as page_name, show_after_complete
            FROM velocity.page_config
            ORDER BY page_name
        """)
        
        available_pages = cursor.fetchall()
        print(f"DEBUG: Returning {len(available_pages)} available pages")
        
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'available_pages': available_pages
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)
