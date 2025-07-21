from django.urls import path, re_path
from django.http import HttpResponse, HttpRequest, JsonResponse
import pylims, json, os
from pydantic import BaseModel, EmailStr, constr, ValidationError, validator
import psycopg
from psycopg.rows import dict_row
from psycopg import sql
import bcrypt
from django.shortcuts import render, redirect

current_directory = os.path.dirname(os.path.abspath(__file__))
self = os.path.basename(current_directory)


def load_automations(params):
    response = {}
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()

    cursor.execute("SELECT asid,name,version,type FROM automation_step ORDER BY name ASC")
    
    results = cursor.fetchall()
    print('step count:',len(results))
    steplist={}
    for result in results:
        steplist[result["asid"]]=result

    cursor.execute("SELECT wfid, name, type, version, steps FROM automation_workflow;")
    
    step_queues={}

    results = cursor.fetchall()
    print('workflow count:',len(results))
    workflows={}
    for result in results:
        workflows[result["wfid"]]=result
    for wf in workflows:
        print('workflow #',wf)
        workflows[wf]["steplist"]=[]
        wfsteps=json.loads(workflows[wf]['steps'])
        for step in wfsteps:
            print("\tStep #",step)
            wf_step = steplist[step]
            cursor.execute("SELECT aqid, (SELECT count(*) FROM automation_queue WHERE in_queue=asq.aqid) as count FROM automation_step_queue asq WHERE workflow=%s and step=%s and pos=%s LIMIT 1;",(wf,step,len(workflows[wf]["steplist"])))
            result = cursor.fetchone()
            if not result == None:
                wf_step["queue"]=result["aqid"]
                wf_step["count"]=result["count"]
            workflows[wf]["steplist"].append(wf_step)

    response["workflows"]=workflows
    response["steps"]=steplist

    cursor.close()
    conn.close()

    if not 'error' in response:
        response['status']='success'
    return response
def queue(request):
    response={}
    data = json.loads(request.body)
    print('data',data)

    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM automation_queue aq JOIN automation_subsample ass ON ass.ssid=aq.subsample JOIN samples ON sid=ass.host JOIN containers ON cid = ass.in_container WHERE in_queue=%s;",(data['id'],))
    results = cursor.fetchall()
    response['samples']=[]
    for result in results:
        response['samples'].append(result)

    cursor.execute("SELECT *, ast.name as step_name, aw.name as workflow_name FROM automation_step_queue asq JOIN automation_step ast ON ast.asid=asq.step JOIN automation_workflow aw ON aw.wfid=asq.workflow WHERE asq.aqid=%s",(data['id'],))
    response['step']=cursor.fetchone()

    cursor.execute("SELECT *, ast.name as step_name, aw.name as workflow_name FROM automation_step_queue asq JOIN automation_step ast ON ast.asid=asq.step JOIN automation_workflow aw ON aw.wfid=asq.workflow WHERE asq.workflow=%s and asq.pos=%s and ast.type!='Function';",(response['step']['workflow'],response['step']['pos']+1))
    response['next']=cursor.fetchone()
    cursor.close()
    conn.close()
    if not 'error' in response:
        response['status']='success'
    return JsonResponse(response)

urlpatterns = [
    path("load_automations/", load_automations, name="load_automations"),
    path('queue/', queue, name='queue'),
]
