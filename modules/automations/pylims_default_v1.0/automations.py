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


def load_automations(params):
    response = {}
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute("SELECT asid,name,version FROM automation_step ORDER BY name ASC")
    
    results = cursor.fetchall()
    print('step count:',len(results))
    steplist={}
    for result in results:
        steplist[result["asid"]]=result

    cursor.execute("SELECT wfid, name, type, version, steps FROM automation_workflow ORDER BY name ASC")
    
    results = cursor.fetchall()
    print('workflow count:',len(results))
    workflows={}
    for result in results:
        workflows[result["wfid"]]=result
    for wf in workflows:
        print('workflow #',wf)
        workflows[wf]["steplist"]=[]
        steps=json.loads(workflows[wf]['steps'])
        for step in steps:
            print("\tStep #",step)
            workflows[wf]["steplist"].append(steplist[step]["name"])

    response["workflows"]=workflows

    cursor.close()
    conn.close()

    if not 'error' in response:
        response['status']='success'
    return response


urlpatterns = [
    path("load_automations/", load_automations, name="load_automations"),
]
