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
@csrf_exempt
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
                           av.status, av.created as version_created
                    FROM velocity.assay a
                    LEFT JOIN velocity.assay_versions av ON a.active_version = av.avid
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
@csrf_exempt
def create_assay(request):
    """
    Create a new assay with initial version
    This function is specifically for creating new assays and can be expanded later
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    # Check permissions
    if not (has_permission(request, 'super_user') or has_permission(request, 'assayconfig_create')):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        data = json.loads(request.body)
        assay_name = data.get('assay_name', '').strip()
        create_initial_version = data.get('create_initial_version', True)  # Default to True for new assays
        
        if not assay_name:
            return JsonResponse({'error': 'Assay name is required'}, status=400)
        
        conn = psycopg.connect(
            dbname=pylims.dbname, 
            user=pylims.dbuser, 
            password=pylims.dbpass, 
            host=pylims.dbhost, 
            port=pylims.dbport, 
            row_factory=dict_row
        )
        cursor = conn.cursor()
        
        # Check if assay name already exists
        cursor.execute("""
            SELECT assayid FROM velocity.assay 
            WHERE LOWER(assay_name) = LOWER(%s) AND visible = true
        """, (assay_name,))
        
        if cursor.fetchone():
            return JsonResponse({'error': 'An assay with this name already exists'}, status=400)
        
        # Create new assay with default values
        cursor.execute("""
            INSERT INTO velocity.assay (assay_name, active_version, archived, visible)
            VALUES (%s, %s, %s, %s)
            RETURNING assayid, assay_name, modified, active_version, archived, visible
        """, (assay_name, None, False, True))  # Start with no active version, not archived, visible
        
        result = cursor.fetchone()
        new_assayid = result['assayid']
        
        # Create initial version if requested
        if create_initial_version:
            version_name = f"{assay_name} init"
            cursor.execute("""
                INSERT INTO velocity.assay_versions 
                (assay, version_name, version_major, version_minor, version_patch, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING avid, version_name, version_major, version_minor, version_patch
            """, (new_assayid, version_name, 1, 0, 0, 'active'))
            
            version_result = cursor.fetchone()
            new_avid = version_result['avid']
            
            # Update the assay to set this as the active version
            cursor.execute("""
                UPDATE velocity.assay 
                SET active_version = %s, modified = CURRENT_TIMESTAMP
                WHERE assayid = %s
                RETURNING assayid, assay_name, modified, active_version
            """, (new_avid, new_assayid))
            
            result = cursor.fetchone()
            message = f'Assay "{assay_name}" created successfully with initial version 1.0'
        else:
            message = f'Assay "{assay_name}" created successfully'
        
        conn.commit()
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'assay': result,
            'message': message
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)


@login_required
@csrf_exempt
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
@csrf_exempt
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
@csrf_exempt
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
@csrf_exempt
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
