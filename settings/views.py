from django.contrib import admin
from django.urls import path, re_path, reverse
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpRequest, JsonResponse
from django.template.defaulttags import register
from django.conf.urls import include
from django.views.decorators.csrf import csrf_exempt
import json, os, sys, subprocess, datetime
from pathlib import Path
from settings import settings
from django.template.loader import get_template
import pylims
import psycopg
from psycopg import sql
from psycopg.rows import dict_row 
from psycopg.pq import Escaping

def handlePost(request):
    if request.method == 'POST':
        try:
            json_data = json.loads(request.body)
            return 200
        except json.JSONDecodeError as e:
            return 400
    return 405
    


def home(request):
    context={}
    context['info']=[]
    with open("VERSION", 'r') as file:
        context['info'].append(['Pylims Version',file.read()])
    context['info'].append(['Python Version',".".join(sys.version.split()[0].split('.')[:2])])
    return redirect('display_queues')
    return render(request, 'index.html', context)

def show_login(request):
    context = {}
    return render(request, 'login.html', context)
def show_logout(request):
    context = {}
    return render(request, 'logout.html', context)

def setup(request):
    print(pylims.term(),pylims.info('building module list'))
    context={}
    #get all available modules 
    context['modules'] = pylims.build_module_dict()
    context['setup']=pylims.get_setup_options()
    context['links']=pylims.build_module_links(request)
    # print(context['modules'])
    return render(request, 'setup.html', context)

def setup_save(request):
    response={}
    response_code = handlePost(request)
    if response_code==400:
        response_data = {'error': 'Invalid JSON data', 'message': str(e)}
        return JsonResponse(response_data, status=400)
    elif response_code==405:
        response_data = {'error': 'Invalid request method', 'message': 'Method not allowed'}
        return JsonResponse(response_data, status=405)
    json_data = json.loads(request.body)
    # print(json_data)
    
    file_path = settings.BASE_DIR / 'json/module_setup.json'
    with open(file_path, 'w+') as json_file:
        json.dump(json_data, json_file, indent=4)
    file_path = settings.BASE_DIR / 'setup_updated.py'
    current_datetime = datetime.datetime.now()
    formatted_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')
    with open(file_path, 'w+') as setupfile:
        setupfile.write(f'updated_datetime = "{formatted_datetime}"\n')
        
    response['msg_success']='Setup saved'
    response['status']='success';
    return JsonResponse(response)
    
def login_password_reset(request):
    return render(request, 'index.html')


def test(test):
    return test