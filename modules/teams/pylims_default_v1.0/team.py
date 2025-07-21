from django.urls import path, re_path
from django.http import HttpResponse, HttpRequest, JsonResponse
import pylims, json, os
from pydantic import BaseModel, EmailStr, constr, ValidationError, validator
import psycopg
from psycopg.rows import dict_row
import bcrypt

current_directory = os.path.dirname(os.path.abspath(__file__))
self = os.path.basename(current_directory)

def test():
    return 'worked?'

def get_teams(params):
    response={}
    response['data']={}
    mods = json.loads(pylims.get_setup_options())
    mod=mods['options']['teams'][self];
    # print('mod',params['modinfo'])
    if not 'userid' in params:
        response['error']='no userid'
        response['status']='failed'
        return response
    # print('getOrg userid',int(params['userid']))
    if 'departments' in mods['options'] and not mods['options']['departments']=='disabled':
        response['departments']=True
    if 'organization' in mods['options'] and not mods['options']['organization']=='disabled':
        response['organization']=True
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    if 'query' in params and 'id' in params['query']:
        cursor.execute("SELECT teams.*, departments.*, organizations.*, ut.utid, ud.udid, uo.uoid FROM teams JOIN departments ON departments.deptid=teams.in_dept JOIN organizations ON organizations.oid=departments.in_org LEFT JOIN user_teams AS ut ON ut.user=%s::integer AND ut.team=teamid LEFT JOIN user_departments AS ud ON ud.user=%s::integer AND ud.dept=deptid LEFT JOIN user_organization AS uo ON uo.user=%s::integer AND uo.org=departments.in_org WHERE teams.teamid = %s::integer LIMIT 1;", (int(params['userid']),int(params['userid']),int(params['userid']),int(params['query']['id'])))
        results = cursor.fetchone()
        
        # Team viewable: 
        # 0 = nobody except admins
        # 1 = only members
        # 2 = members of parent departments
        # 3 = members of parent organization
        # 4 = any logged in user
        # 5 = public
        
        if results==None:
            response['error']='Team not found'
            response['status']='failed'
            return response
            
        accepted_permissions=['departments_edit']   
        if results['viewable']==0 and not pylims.adminauthmatch(pylims.loaduser_admin(params['userid']),accepted_permissions):
            response['error']='Team not viewable to non-admins'
            response['status']='failed'
            return response
            
        if results['viewable']==1 and not results['utid']:
            response['error']='Team not viewable to non-members'
            response['status']='failed'
            return response
        
        if results['viewable']==2 and not results['udid']:
            response['error']='Team not viewable to non-organization members'
            response['status']='failed'
            return response 
        
        if results['viewable']==3 and not results['uoid']:
            response['error']='Team not viewable to non-organization members'
            response['status']='failed'
            return response 
        
        if results['viewable']==4 and not params['userid']:
            response['error']='Team not viewable to logged out users'
            response['status']='failed'
            return response
        
        
        
        response['data']=results
        if not 'error' in response:
            response['status']='success'
        return response


    cursor.execute("SELECT * FROM user_teams JOIN teams ON teamid=user_teams.team WHERE user_teams.user = %s::integer;", (int(params['userid']),))

    results = cursor.fetchone()
    # print('results',results)
    if results==None:
        cursor.execute("""SELECT 
            column_name
        FROM information_schema.columns
        WHERE table_name = 'user_teams'
        UNION
        SELECT 
            column_name
        FROM information_schema.columns
        WHERE table_name = 'teams';""")
        results = cursor.fetchall()
        
        for result in results:
            if result['column_name']=='teamid' or result['column_name']=='utid':
                continue
            response['data'][result['column_name']]=''
        response['data']['team_name']='Oh No :('
        response['data']['team_description']='you have not been added to any teams yet.'
        # response['data']['image']='data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiIHN0YW5kYWxvbmU9Im5vIj8+CjwhRE9DVFlQRSBzdmcgUFVCTElDICItLy9XM0MvL0RURCBTVkcgMS4xLy9FTiIgImh0dHA6Ly93d3cudzMub3JnL0dyYXBoaWNzL1NWRy8xLjEvRFREL3N2ZzExLmR0ZCI+Cjxzdmcgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgdmlld0JveD0iMCAwIDY0IDY0IiB2ZXJzaW9uPSIxLjEiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgeG1sbnM6eGxpbms9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkveGxpbmsiIHhtbDpzcGFjZT0icHJlc2VydmUiIHhtbG5zOnNlcmlmPSJodHRwOi8vd3d3LnNlcmlmLmNvbS8iIHN0eWxlPSJmaWxsLXJ1bGU6ZXZlbm9kZDtjbGlwLXJ1bGU6ZXZlbm9kZDtzdHJva2UtbGluZWpvaW46cm91bmQ7c3Ryb2tlLW1pdGVybGltaXQ6MjsiPgogICAgPHBhdGggZD0iTTI1LjM5MSw2My42MThMMTAuODY2LDYzLjYxOEM5LjgyOSw2My42MTggOC45ODYsNjEuNzM0IDguOTg2LDYwLjY5Nkw4Ljk4Niw0NS40MjhDOC45ODYsNDQuMzkgOS44MjksNDMuNTQ4IDEwLjg2Niw0My41NDhMMTIuMzg0LDQzLjU0OEwxMi4zODQsNDUuNzQ5QzEyLjM4NCw1MC41NjQgMTYuMjg3LDU0LjQ2NyAyMS4xMDIsNTQuNDY3TDI3Ljg0Myw1NC40NjNDMjcuODQzLDU0LjQ2MyAzNC43OTgsNTQuNTMxIDM0LjcwOCw1Ni41NDNDMzQuNjk2LDU2LjgwOCAzMS44MzIsNTcuNjIgMjUuMzE2LDU3LjMwOUMyMC40MDIsNTcuMDc0IDIwLjQ1NSw1OS4xMDQgMjUuMzA5LDU4Ljg3QzMxLjE0NSw1OC41OSAzNC42MTQsNTguNjM5IDM0LjYwNiw1OS4wMTJDMzQuNTAyLDY0LjE3NSAyNS4zOTEsNjMuNjE4IDI1LjM5MSw2My42MThaTTQ1LjY3OSw2Mi41NzdMNTMuNDU5LDYyLjU3N0M1NC40OTcsNjIuNTc3IDU1LjMzOSw2MS43MzQgNTUuMzM5LDYwLjY5Nkw1NS4zMzksNDUuNDI4QzU1LjMzOSw0NC4zOSA1NC40OTcsNDMuNTQ4IDUzLjQ1OSw0My41NDhMNTEuOTQyLDQzLjU0OEw1MS45NDIsNDUuNzQ5QzUxLjk0Miw1MC41NjQgNDguMDM4LDU0LjQ2NyA0My4yMjQsNTQuNDY3QzQzLjIyMyw1NC40NjcgNDMuMjIyLDU0LjQ2NyA0My4yMjIsNTQuNDY3TDQzLjIyNyw1NC40NjNDNDMuMjI3LDU0LjQ2MyAzNi4yNzMsNTQuNTMxIDM2LjM2Myw1Ni41NDNDMzYuMzc1LDU2LjgwOCAzOS4yMzgsNTcuNjIgNDUuNzU1LDU3LjMwOUM1MC42NjgsNTcuMDc0IDUwLjYxNiw1OS4xMDQgNDUuNzYyLDU4Ljg3QzM5LjkyNiw1OC41OSAzNi40NzQsNTguNjM5IDM2LjQ2NCw1OS4wMTJDMzYuMzYsNjIuOTY3IDQ1LjY3OSw2Mi41NzcgNDUuNjc5LDYyLjU3N1pNMTIuMzUzLDM3LjQxTDEyLjM1Myw0Mi4wMzRMMTAuOTM4LDQyLjAzNEM5LjI1Miw0Mi4wMzQgNy44ODYsNDMuNCA3Ljg4Niw0NS4wODZDNy44ODYsNDguMzg3IDcuODg2LDUzLjE4NCA3Ljg4Niw1My4xODRMNS40NjUsNTMuMTg0QzQuMjQsNTMuMTg0IDMuMjQ0LDUyLjE4OSAzLjI0NCw1MC45NjNMMy4yNDQsMzkuNjMxQzMuMjQ0LDM4LjQwNSA0LjI0LDM3LjQxIDUuNDY1LDM3LjQxTDEyLjM1MywzNy40MVpNNTEuOTU2LDM3LjQxTDUxLjk1Niw0Mi4wMzRMNTMuMzcxLDQyLjAzNEM1NS4wNTcsNDIuMDM0IDU2LjQyMyw0My40IDU2LjQyMyw0NS4wODZDNTYuNDIzLDQ4LjM2NSA1Ni40MjMsNTMuMTA5IDU2LjQyMyw1My4xMDlMNTguODQzLDUzLjEwOUM2MC4wNjksNTMuMTA5IDYxLjA2NSw1Mi4xMTQgNjEuMDY1LDUwLjg4OEw2MS4wNjUsMzkuNjMxQzYxLjA2NSwzOC40MDUgNjAuMDY5LDM3LjQxIDU4Ljg0MywzNy40MUw1MS45NTYsMzcuNDFaTTEyLjM1MywzMkwyLjI0NSwzMkMxLjg3NCwzMiAxLjUxNywzMi4xNDggMS4yNTUsMzIuNDFDMC45OTIsMzIuNjczIDAuODQ0LDMzLjAyOSAwLjg0NCwzMy40MDFDMC44NDQsMzMuOTY4IDAuODQ0LDM0LjYyMiAwLjg0NCwzNS4xOUMwLjg0NCwzNS41NjEgMC45OTIsMzUuOTE4IDEuMjU1LDM2LjE4MUMxLjUxNywzNi40NDMgMS44NzQsMzYuNTkxIDIuMjQ1LDM2LjU5MUM1LjMxMywzNi41OTEgMTIuMzUzLDM2LjU5MSAxMi4zNTMsMzYuNTkxTDEyLjM1MywzMlpNNTEuOTU2LDMyTDYyLjA2NCwzMkM2Mi40MzUsMzIgNjIuNzkxLDMyLjE0OCA2My4wNTQsMzIuNDFDNjMuMzE3LDMyLjY3MyA2My40NjQsMzMuMDI5IDYzLjQ2NCwzMy40MDFDNjMuNDY0LDMzLjk2OCA2My40NjQsMzQuNjIyIDYzLjQ2NCwzNS4xOUM2My40NjQsMzUuNTYxIDYzLjMxNywzNS45MTggNjMuMDU0LDM2LjE4MUM2Mi43OTEsMzYuNDQzIDYyLjQzNSwzNi41OTEgNjIuMDY0LDM2LjU5MUM1OC45OTYsMzYuNTkxIDUxLjk1NiwzNi41OTEgNTEuOTU2LDM2LjU5MUw1MS45NTYsMzJaTTUxLjk1NiwzMS4xNDhMNTEuOTU2LDI2LjUyNUw1My4zNzEsMjYuNTI1QzU1LjA1NywyNi41MjUgNTYuNDIzLDI1LjE1OCA1Ni40MjMsMjMuNDcyQzU2LjQyMywxOC45OTEgNTYuNDIzLDExLjE1NiA1Ni40MjMsMTEuMTU2TDU4Ljg0MywxMS4xNTZDNjAuMDY5LDExLjE1NiA2MS4wNjUsMTIuMTUxIDYxLjA2NSwxMy4zNzdMNjEuMDY1LDI4LjkyN0M2MS4wNjUsMzAuMTUzIDYwLjA2OSwzMS4xNDggNTguODQzLDMxLjE0OEw1MS45NTYsMzEuMTQ4Wk0xMi4zNTMsMzEuMTQ4TDEyLjM1MywyNi41MjVMMTAuOTM4LDI2LjUyNUM5LjI1MiwyNi41MjUgNy44ODYsMjUuMTU4IDcuODg2LDIzLjQ3MkM3Ljg4NiwxOC44MjggNy44ODYsMTAuNTE5IDcuODg2LDEwLjUxOUw1LjQ2NSwxMC41MTlDNC4yNCwxMC41MTkgMy4yNDQsMTEuNTE0IDMuMjQ0LDEyLjc0TDMuMjQ0LDI4LjkyN0MzLjI0NCwzMC4xNTMgNC4yNCwzMS4xNDggNS40NjUsMzEuMTQ4TDEyLjM1MywzMS4xNDhaTTIxLjEwMywxLjU0NUwxMC44NjYsMS41NDVDOS44MjksMS41NDUgOC45ODYsMi4zODggOC45ODYsMy40MjZMOC45ODYsMjMuODE3QzguOTg2LDI0Ljg1NSA5LjgyOSwyNS42OTggMTAuODY2LDI1LjY5OEwxMi4zODQsMjUuNjk4TDEyLjM4NCwyMy40OTZDMTIuMzg0LDE4LjY4MSAxNi4yODcsMTQuNzc4IDIxLjEwMiwxNC43NzhDMjEuMTAzLDE0Ljc3OCAyMS4xMDMsMTQuNzc4IDIxLjEwMywxNC43NzhMMjEuMTAzLDEuNTQ1Wk00My4yMjIsMS4wNTdMNTMuNDU5LDEuMDU3QzU0LjQ5NywxLjA1NyA1NS4zMzksMS45IDU1LjMzOSwyLjkzOEw1NS4zMzksMjMuODE3QzU1LjMzOSwyNC44NTUgNTQuNDk3LDI1LjY5OCA1My40NTksMjUuNjk4TDUxLjk0MiwyNS42OThMNTEuOTQyLDIzLjQ5NkM1MS45NDIsMTguNjgxIDQ4LjAzOCwxNC43NzggNDMuMjI0LDE0Ljc3OEM0My4yMjMsMTQuNzc4IDQzLjIyMiwxNC43NzggNDMuMjIyLDE0Ljc3OEw0My4yMjIsMS4wNTdaIiBzdHlsZT0iZmlsbDp1cmwoI19MaW5lYXIxKTsiLz4KICAgIDxwYXRoIGQ9Ik01MS4xMTEsMjQuMjg0QzUxLjExMSwxOS40OTkgNDcuMjI2LDE1LjYxNCA0Mi40NDEsMTUuNjE0TDIxLjgwMywxNS42MTRDMTcuMDE4LDE1LjYxNCAxMy4xMzMsMTkuNDk5IDEzLjEzMywyNC4yODRMMTMuMTMzLDQ1LjE2NUMxMy4xMzMsNDkuOTUgMTcuMDE4LDUzLjgzNSAyMS44MDMsNTMuODM1TDQyLjQ0MSw1My44MzVDNDcuMjI2LDUzLjgzNSA1MS4xMTEsNDkuOTUgNTEuMTExLDQ1LjE2NUw1MS4xMTEsMjQuMjg0Wk0yNC4wMTIsNDUuMjk3QzI1LjYxNyw0NS4yOTcgMjYuOTIsNDYuNjAxIDI2LjkyLDQ4LjIwNkMyNi45Miw0OS44MTEgMjUuNjE3LDUxLjExNSAyNC4wMTIsNTEuMTE1QzIyLjQwNiw1MS4xMTUgMjEuMTAzLDQ5LjgxMSAyMS4xMDMsNDguMjA2QzIxLjEwMyw0Ni42MDEgMjIuNDA2LDQ1LjI5NyAyNC4wMTIsNDUuMjk3Wk00MC4zMTQsNDUuMjk3QzQxLjkxOSw0NS4yOTcgNDMuMjIyLDQ2LjYwMSA0My4yMjIsNDguMjA2QzQzLjIyMiw0OS44MTEgNDEuOTE5LDUxLjExNSA0MC4zMTQsNTEuMTE1QzM4LjcwOCw1MS4xMTUgMzcuNDA1LDQ5LjgxMSAzNy40MDUsNDguMjA2QzM3LjQwNSw0Ni42MDEgMzguNzA4LDQ1LjI5NyA0MC4zMTQsNDUuMjk3WiIgc3R5bGU9ImZpbGw6dXJsKCNfTGluZWFyMik7Ii8+CiAgICA8ZGVmcz4KICAgICAgICA8bGluZWFyR3JhZGllbnQgaWQ9Il9MaW5lYXIxIiB4MT0iMCIgeTE9IjAiIHgyPSIxIiB5Mj0iMCIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiIGdyYWRpZW50VHJhbnNmb3JtPSJtYXRyaXgoNDEuODgwNiwwLDAsNDkuODUwMSw5LjIyOTk5LDI4LjY2NTgpIj48c3RvcCBvZmZzZXQ9IjAiIHN0eWxlPSJzdG9wLWNvbG9yOnJnYig0OCwxMDUsMTUyKTtzdG9wLW9wYWNpdHk6MSIvPjxzdG9wIG9mZnNldD0iMSIgc3R5bGU9InN0b3AtY29sb3I6cmdiKDEwNywxNDYsMTc3KTtzdG9wLW9wYWNpdHk6MSIvPjwvbGluZWFyR3JhZGllbnQ+CiAgICAgICAgPGxpbmVhckdyYWRpZW50IGlkPSJfTGluZWFyMiIgeDE9IjAiIHkxPSIwIiB4Mj0iMSIgeTI9IjAiIGdyYWRpZW50VW5pdHM9InVzZXJTcGFjZU9uVXNlIiBncmFkaWVudFRyYW5zZm9ybT0ibWF0cml4KDM3Ljk3NzEsMCwwLDM4LjIyMTEsMTMuMTMzNCwzNC43MjQzKSI+PHN0b3Agb2Zmc2V0PSIwIiBzdHlsZT0ic3RvcC1jb2xvcjpyZ2IoMzUsNzcsMTExKTtzdG9wLW9wYWNpdHk6MSIvPjxzdG9wIG9mZnNldD0iMSIgc3R5bGU9InN0b3AtY29sb3I6cmdiKDc0LDExMSwxNDApO3N0b3Atb3BhY2l0eToxIi8+PC9saW5lYXJHcmFkaWVudD4KICAgIDwvZGVmcz4KPC9zdmc+Cg=='
        response['status']='no dept'
        return response
    else:
        response['data']=results
    cursor.close()
    conn.close()
    
    
    
    if not 'error' in response:
        response['status']='success'
    return response
    
