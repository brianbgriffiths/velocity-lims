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
    """
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
        
        # Get all assays with their active versions
        cursor.execute("""
            SELECT a.assayid, a.assay_name, a.modified, a.active_version,
                   av.version_name, av.version_major, av.version_minor, av.version_patch,
                   av.status, av.created as version_created
            FROM velocity.assay a
            LEFT JOIN velocity.assay_versions av ON a.active_version = av.avid
            ORDER BY a.assay_name
        """)
        
        context['assays'] = cursor.fetchall()
        
        # Get all versions for the dropdown (grouped by assay)
        cursor.execute("""
            SELECT av.avid, av.version_name, av.assay, av.version_major, av.version_minor, av.version_patch,
                   a.assay_name
            FROM velocity.assay_versions av
            JOIN velocity.assay a ON av.assay = a.assayid
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
def save_assay(request):
    """
    Save a new assay or update an existing one
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    # Check permissions
    if not (has_permission(request, 'super_user') or 
            has_permission(request, 'assayconfig_create') or 
            has_permission(request, 'assayconfig_edit')):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        data = json.loads(request.body)
        assay_name = data.get('assay_name', '').strip()
        active_version = data.get('active_version')
        assayid = data.get('assayid')
        create_initial_version = data.get('create_initial_version', False)
        
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
        
        if assayid:
            # Update existing assay
            cursor.execute("""
                UPDATE velocity.assay 
                SET assay_name = %s, active_version = %s, modified = CURRENT_TIMESTAMP
                WHERE assayid = %s
                RETURNING assayid, assay_name, modified, active_version
            """, (assay_name, active_version, assayid))
            result = cursor.fetchone()
            message = 'Assay updated successfully'
        else:
            # Create new assay
            cursor.execute("""
                INSERT INTO velocity.assay (assay_name, active_version)
                VALUES (%s, %s)
                RETURNING assayid, assay_name, modified, active_version
            """, (assay_name, None))  # Start with no active version
            
            result = cursor.fetchone()
            new_assayid = result['assayid']
            
            # If creating initial version, create version 1.0
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
                message = f'Assay created successfully with initial version 1.0 ("{version_name}")'
            else:
                message = 'Assay created successfully'
        
        conn.commit()
        conn.close()
        
        return JsonResponse({
            'success': True,
            'assay': result,
            'message': message
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
            'success': True,
            'assay': assay
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)
