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
    modules = json.loads(pylims.build_module_dict())
    file_path = settings.BASE_DIR / 'json/module_setup.json'
    with open(file_path, 'r') as json_file:
        setup = json.load(json_file)
    context['links']=pylims.build_module_links(request)
    context['info']=[]
    with open("VERSION", 'r') as file:
        context['info'].append(['Pylims Version',file.read()])
    context['info'].append(['Python Version',".".join(sys.version.split()[0].split('.')[:2])])
    # print('links',context['links'])
    # print(setup)
    # if 'account_creation' in setup and not setup['account_creation']=='disabled':
        # print('default template',modules["account_creation"][setup["account_creation"]]["templates"][modules["account_creation"][setup["account_creation"]]["default_template"]][1])
        # return render(request, f'account_creation/{modules["account_creation"][setup["account_creation"]]["templates"][modules["account_creation"][setup["account_creation"]]["default_template"]][1]}', context)
    return render(request, 'index.html', context)

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

def mod_resolver(request, mod, page=False):
    import importlib
    
    context={}
    context['links']=pylims.build_module_links(request)
    
    settings=json.loads(pylims.get_setup_options())
    mods = json.loads(pylims.build_module_dict())

    authrule = mods[mod][settings['setup'][mod]]['authentication']
    if 'userid' in request.session and request.session['userid']>0:
        #logged in
        # print('session userid',request.session['userid'])
        if authrule=='loggedout':
            print(pylims.term(),pylims.error('user is already logged in'))
            return redirect('home')
        context['user']={}
        context['user']['userid']=request.session['userid']
        # if 'admin' in request.session:
            # for permission in request.session['admin']:
                # print('ADMIN MODE:',permission)          
    
    context['active_mods']={}
    for amod in settings['setup']:
        if settings['setup'][amod]!='disabled':
            context['active_mods'][amod]=settings['setup'][amod];
            pylims.active_mods[amod]=settings['setup'][amod];
    
    if page==False:
        # print('no page specicified.')
        if 'default_template' in mods[mod][settings['setup'][mod]]: 
            default_template_index = mods[mod][settings['setup'][mod]]['default_template']
            default_template = mods[mod][settings['setup'][mod]]['templates'][default_template_index]
            page = default_template_index.split('.')[0]
            print(pylims.term(),'loading default template', pylims.info(page))
        else:
            print(pylims.term(),pylims.error('no default template'));
            return redirect('home')
    
    conn = psycopg.connect(dbname=pylims.dbname, user=pylims.dbuser, password=pylims.dbpass, host=pylims.dbhost, port=pylims.dbport, row_factory=dict_row)
    cursor = conn.cursor()
    
    context['admin']={}
    if 'userid' in request.session and request.session['userid']>0:
        query = sql.SQL("""
            SELECT admin.permission, user_admin.value
            FROM user_admin
            JOIN admin ON admin.aid = user_admin.permission
            WHERE user_admin.USER = {}
        """).format(sql.Literal(request.session['userid']))
        
        cursor.execute(query)
        result = cursor.fetchall()
        # print('result:', result)
        for permission in result:
            # print('\t',permission['permission'])
            context['admin'][permission['permission']]=permission['value']
        print(pylims.term(),'Admin Permissions: ',context['admin'])    
        adminlinks=''
        if 'admin_templates' in mods[mod][settings['setup'][mod]]:
            for adminlink in mods[mod][settings['setup'][mod]]['admin_templates']:
                if pylims.adminauthmatch(context['admin'],mods[mod][settings['setup'][mod]]['admin_templates'][adminlink]['permission_needed']) and mods[mod][settings["setup"][mod]]["admin_templates"][adminlink]['display_link']==True:
                    adminmod=mod
                    # if "module" in mods[mod][settings["setup"][mod]]["admin_templates"][adminlink]:
                    #     adminmod=adminlink
                        
                    adminlinks+=f'<span class="admin_link"><a href="/modules/{adminmod}/{adminlink.split(".")[0]}">{mods[mod][settings["setup"][mod]]["admin_templates"][adminlink]["name"]}</a></span>'          
        if 'admin' in context and len(context['admin']) > 0:
            context['adminlinks']=f'<div id="adminlinks">Admin: {adminlinks}</div>'
    
    #check verification
    if f'{page}.html' in mods[mod][settings['setup'][mod]]['templates']:
        template = mods[mod][settings['setup'][mod]]['templates'][f'{page}.html']
        match=pylims.authmatch(pylims.loggedin(request),template['authentication'])
        # print('match=',match)
        if match==False:
            print(pylims.term(),page,pylims.error('Authentication not granted.'))
            return redirect('home')
    elif f'{page}.html' in mods[mod][settings['setup'][mod]]['admin_templates']:
        if 'admin' in context and len(context['admin']) == 0:
            print(pylims.term(),page,pylims.error('User is not an admin.'))
            return redirect('home')
        # print(pylims.term(),pylims.info('requested admin template:'),page)
        template = mods[mod][settings['setup'][mod]]['admin_templates'][f'{page}.html']
        match=pylims.adminauthmatch(context['admin'],template['permission_needed'])
        # print('match=',match)
        if match==False:
            print(pylims.term(),page,pylims.error('Authentication not granted.'))
            return redirect('home')
    else:
        print(pylims.term(),page,pylims.error('Template not found.'))
        return redirect('home')
    
    
    if 'load_script_function' in mods[mod][settings['setup'][mod]]:
        loadscript = mods[mod][settings['setup'][mod]]['load_script_function']
        print('loadscript',mods[mod][settings['setup'][mod]]['scripts'][loadscript[0]])
        module_to_import = importlib.import_module(mods[mod][settings['setup'][mod]]['scripts'][loadscript[0]])
        function_to_call = getattr(module_to_import, loadscript[1])
        options_to_send = {}
        options_to_send['admin']=context['admin']
        options_to_send['adminlinks']=context['adminlinks']
        
        if len(request.GET)>0:
            options_to_send['query']={}
            for query in request.GET:
                options_to_send['query'][query]=request.GET.get(query, None)
        if 'user' in loadscript[2]:
            options_to_send['userid']=request.session['userid']
        options_to_send['modinfo']=mods[mod][settings['setup'][mod]]
        options_to_send['active_mods']=context['active_mods']
        print(pylims.term(),'load script:',pylims.info(loadscript[1]))
        context['mod_data']=function_to_call(options_to_send)
        # print(pylims.term(),pylims.info('loadscript moddata'),context['mod_data'])
    else:
        print('no loadscript')
            
    context['mod_options']=json.dumps(settings['options'][mod][settings['setup'][mod]])
    
    context['url']=f'mod_{mod}';
    if 'setup_options' in mods[mod][settings['setup'][mod]]:
        context["mod"]=mods[mod][settings['setup'][mod]]['setup_options']
    else:
        context["mod"]={}
    
    
    print(pylims.term(),pylims.info('Loading page'),context)
    print(pylims.term(),pylims.info('Loading page'),f'{mod}/{page}.html')
    return render(request, f'{mod}/{page}.html', context)
    
def login_password_reset(request):
    return render(request, 'index.html')


def test(test):
    return test