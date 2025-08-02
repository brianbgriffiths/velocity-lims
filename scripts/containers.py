"""
Containers management for Velocity LIMS
Handles container type creation and management
"""

import json
import psycopg
from psycopg.rows import dict_row
from django.shortcuts import render
from django.http import JsonResponse
from settings.views import context_init, has_permission, login_required
import pylims


@login_required
def settings_containers(request):
    """
    Display container types management page
    """
    # Check permissions
    if not (has_permission(request, 'super_user') or has_permission(request, 'container_any')):
        return render(request, 'settings.html', {
            'error': 'You do not have permission to access container settings.'
        })
    
    try:
        conn = psycopg.connect(
            dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, 
            host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row
        )
        cursor = conn.cursor()
        
        # Get all container types from container_config
        cursor.execute("""
            SELECT cid, type_name, rows, columns, well_type, border_type, color,
                   restricted_well_map, special_well_map, corner_types,
                   margin_width, well_padding
            FROM velocity.container_config 
            ORDER BY type_name
        """)
        
        container_types = cursor.fetchall()
        
        conn.close()
        
        # Initialize context
        context = context_init(request)
        context.update({
            'container_types': container_types,
            'has_container_types': len(container_types) > 0,
            'can_create': has_permission(request, 'super_user') or has_permission(request, 'container_create'),
            'can_archive': has_permission(request, 'super_user') or has_permission(request, 'container_archive')
        })
        
        return render(request, 'settings_containers.html', context)
        
    except Exception as e:
        return render(request, 'settings_containers.html', {
            'error': f'Database error: {str(e)}'
        })


@login_required
def create_container_type(request):
    """
    Create a new container type configuration
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    # Check permissions
    if not (has_permission(request, 'super_user') or has_permission(request, 'container_create')):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        data = json.loads(request.body)
        type_name = data.get('type_name', '').strip()
        rows = int(data.get('rows', 8))
        columns = int(data.get('columns', 12))
        well_type = int(data.get('well_type', 1))
        border_type = int(data.get('border_type', 1))
        color = int(data.get('color', 1))
        restricted_wells = data.get('restricted_wells', [])
        special_wells = data.get('special_wells', [])
        corner_types = data.get('corner_types', [1, 1, 1, 1])
        margin_width = int(data.get('margin_width', 2))
        well_padding = int(data.get('well_padding', 2))
        
        if not type_name:
            return JsonResponse({'error': 'Container type name is required'}, status=400)
        
        if rows < 1 or rows > 50:
            return JsonResponse({'error': 'Rows must be between 1 and 50'}, status=400)
        
        if columns < 1 or columns > 50:
            return JsonResponse({'error': 'Columns must be between 1 and 50'}, status=400)
        
        if well_type < 1 or well_type > 10:
            return JsonResponse({'error': 'Invalid well type'}, status=400)
        
        if border_type < 1 or border_type > 10:
            return JsonResponse({'error': 'Invalid border type'}, status=400)
        
        if color < 1 or color > 20:
            return JsonResponse({'error': 'Invalid color selection'}, status=400)
        
        if margin_width < 0 or margin_width > 100:
            return JsonResponse({'error': 'Margin width must be between 0 and 100'}, status=400)
        
        if well_padding < 0 or well_padding > 20:
            return JsonResponse({'error': 'Well padding must be between 0 and 20'}, status=400)
        
        # Validate corner_types array
        if not isinstance(corner_types, list) or len(corner_types) != 4:
            return JsonResponse({'error': 'Corner types must be an array of 4 values'}, status=400)
        
        for corner_type in corner_types:
            if not isinstance(corner_type, int) or corner_type < 1 or corner_type > 10:
                return JsonResponse({'error': 'Invalid corner type value'}, status=400)
            return JsonResponse({'error': 'Invalid color selection'}, status=400)
        
        conn = psycopg.connect(
            dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, 
            host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row
        )
        cursor = conn.cursor()
        
        # Check for duplicate type name
        cursor.execute("""
            SELECT cid FROM velocity.container_config 
            WHERE type_name = %s
        """, (type_name,))
        
        if cursor.fetchone():
            return JsonResponse({'error': 'Container type name already exists'}, status=400)
        
        # Insert new container type
        cursor.execute("""
            INSERT INTO velocity.container_config 
            (type_name, rows, columns, well_type, border_type, color, 
             restricted_well_map, special_well_map, corner_types, margin_width, well_padding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING cid, type_name, rows, columns, well_type, border_type, color
        """, (type_name, rows, columns, well_type, border_type, color, 
              json.dumps(restricted_wells), json.dumps(special_wells), json.dumps(corner_types),
              margin_width, well_padding))
        
        result = cursor.fetchone()
        
        conn.commit()
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'container_type': result,
            'message': f'Container type "{type_name}" created successfully'
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Invalid JSON data: {str(e)}'}, status=400)
    except ValueError as e:
        return JsonResponse({'error': f'Invalid numeric value: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)


@login_required
def get_container_type_details(request):
    """
    Get container type details for display
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    # Check permissions
    if not (has_permission(request, 'super_user') or has_permission(request, 'container_any')):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        data = json.loads(request.body)
        cid = data.get('cid')
        
        if not cid:
            return JsonResponse({'error': 'Container type ID is required'}, status=400)
        
        conn = psycopg.connect(
            dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, 
            host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cid, type_name, rows, columns, well_type, border_type, color,
                   restricted_well_map, special_well_map, corner_types,
                   margin_width, well_padding
            FROM velocity.container_config 
            WHERE cid = %s
        """, (cid,))
        
        container_type = cursor.fetchone()
        
        if not container_type:
            return JsonResponse({'error': 'Container type not found'}, status=404)
        
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'container_type': container_type
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Invalid JSON data: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)


@login_required
def delete_container_type(request):
    """
    Delete a container type (only if not in use)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    # Check permissions
    if not (has_permission(request, 'super_user') or has_permission(request, 'container_archive')):
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        data = json.loads(request.body)
        cid = data.get('cid')
        
        if not cid:
            return JsonResponse({'error': 'Container type ID is required'}, status=400)
        
        conn = psycopg.connect(
            dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, 
            host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row
        )
        cursor = conn.cursor()
        
        # Check if container type is in use
        cursor.execute("""
            SELECT COUNT(*) as count FROM velocity.containers 
            WHERE container_type = %s
        """, (cid,))
        
        usage_check = cursor.fetchone()
        if usage_check and usage_check['count'] > 0:
            return JsonResponse({
                'error': f'Cannot delete container type - it is currently in use by {usage_check["count"]} containers'
            }, status=400)
        
        # Get container type name before deletion
        cursor.execute("""
            SELECT type_name FROM velocity.container_config WHERE cid = %s
        """, (cid,))
        
        type_info = cursor.fetchone()
        if not type_info:
            return JsonResponse({'error': 'Container type not found'}, status=404)
        
        # Delete the container type
        cursor.execute("""
            DELETE FROM velocity.container_config WHERE cid = %s
        """, (cid,))
        
        conn.commit()
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Container type "{type_info["type_name"]}" deleted successfully'
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Invalid JSON data: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)


