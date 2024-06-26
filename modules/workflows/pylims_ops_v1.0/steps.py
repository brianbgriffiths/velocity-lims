from django.urls import path, re_path
from django.http import HttpResponse, HttpRequest, JsonResponse
import pylims, json, os
from pydantic import BaseModel, EmailStr, constr, ValidationError, validator
import psycopg
from psycopg.rows import dict_row
from psycopg import sql
import bcrypt

current_directory = os.path.dirname(os.path.abspath(__file__))
self = os.path.basename(current_directory)

def load_steps(params):
    response={}
    response['data']={}
    mods = json.loads(pylims.get_setup_options())
    mod=mods['options']['organization'][self];
    # print('mod',params['modinfo'])
    if not 'userid' in params:
        response['error']='no userid'
        response['status']='failed'
        return response
    # print('getOrg userid',int(params['userid']))
    if 'departments' in mods['setup'] and not mods['setup']['departments']=='disabled':
        response['data']['departments']=mods['setup']['departments']
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    
    if 'query' in params and 'id' in params['query']:
        cursor.execute("SELECT organizations.*, uo.uoid FROM organizations LEFT JOIN user_organization AS uo ON uo.user=%s::integer AND uo.org=oid WHERE organizations.oid = %s::integer LIMIT 1;", (int(params['userid']),int(params['query']['id'])))
        results = cursor.fetchone()
        
        # Department viewable: 
        # 0 = nobody except admins
        # 1 = only members
        # 2 = members of parent departments
        # 3 = members of parent organization
        # 4 = any logged in user
        # 5 = public
        
        
        if not 'error' in response:
            response['status']='success'
        return response
    
    
            
    cursor.execute("SELECT * FROM user_organization JOIN organizations ON oid=user_organization.org WHERE user_organization.user = %s::integer;", (int(params['userid']),))
    results = cursor.fetchall()
      

    if 'teams' in pylims.active_mods:
        team_module = pylims.modules['teams']['team']
        print(pylims.term(),pylims.info(team_module.test()))
    # if 'departments' in mods['setup'] and not mods['setup']['departments']=='disabled':
        # if mod['show_departments']=='true':
            
            # oids_str = ",".join([str(oid) for oid in oids])
            # print('oids',oids_str)
            # query = "SELECT * FROM departments WHERE in_org IN (%s) ORDER BY dept_name ASC"
            # cursor.execute(query, (oids_str,))
            
            # results = cursor.fetchall()
            # print('department count:',len(results))
            # response['data']['departments']=results
            # deptids = [int(row["deptid"]) for row in results]
    # if 'teams' in mods['setup'] and not mods['setup']['teams']=='disabled':
        # if mod['show_teams']=='true':
            # if not deptids==None:
                # query = "SELECT * FROM teams WHERE in_dept = ANY(%s) ORDER BY teamid ASC"
                # cursor.execute(query, (deptids,))
            
            # results = cursor.fetchall()
            # print('Team count:',len(results))
            # response['data']['teams']=results
    
    cursor.close()
    conn.close()
    
    
    
    if not 'error' in response:
        response['status']='success'
    return response



urlpatterns=[
    path('load_spaces/', load_spaces, name="load_spaces"),
    ]
    
