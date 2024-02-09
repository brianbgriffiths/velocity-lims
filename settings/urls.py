"""
URL configuration for pylims project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import json, sys, importlib, os
from importlib.machinery import SourceFileLoader
from pathlib import Path
from django.contrib import admin
from django.urls import path
from settings import views, settings
from colorama import Fore, Back, Style, just_fix_windows_console
just_fix_windows_console()
import pylims
from django.views import static


print(pylims.term(),"Starting Pylims Server")

urlpatterns = [
    path('', views.home, name="home"),
    path('setup/', views.setup, name="setup"),
    path('setup_save/', views.setup_save, name="setup_save"),
    path('modules/<str:mod>/<str:page>/', views.mod_resolver, name='mod_resolver'),
    path('modules/<str:mod>/', views.mod_resolver, name='mod_resolver'),
]

modules = json.loads(pylims.build_module_dict())
file_path = settings.BASE_DIR / 'json/module_setup.json'
with open(file_path, 'r') as json_file:
    setup = json.load(json_file)

# print('URL setup',setup['setup'])
# print('URL modules',modules)

for mod in setup['setup']:
    
    
    if setup['setup'][mod]=='disabled':
        print(pylims.term(),f'skipping {mod}: {pylims.warning("disabled")}')
        continue
    if not setup['setup'][mod] in modules[mod]:
        print(pylims.term(),pylims.error('mod not found in src/modules'))
        continue    
    if modules[mod][setup['setup'][mod]]['type']=='error':
        print(pylims.term(),f'initializing {mod}:{pylims.error("not found")}')
        continue
    print(pylims.term(),f"initializing {mod}: {pylims.info(setup['setup'][mod])}")    
    # print(mod, modules[mod][setup['setup'][mod]]['scripts'])
    folder_path = str(settings.BASE_DIR / f'modules/{mod}/{setup['setup'][mod]}')
    for script in modules[mod][setup['setup'][mod]]['scripts']:
        module_path=os.path.join(folder_path,script)
        # print(f"loading {folder_path}/{script}")
        your_module = SourceFileLoader(script, module_path).load_module()
        try:
            urls = getattr(your_module, 'urlpatterns')
            for url in urls:
                url.pattern._route = f'mod_{mod}/' + str(url.pattern)
            # print(f'urls for {script}:',urls)
            urlpatterns=urlpatterns+urls
            # url(fr"^modules/{mod}/{setup['setup'][mod]}/(?P<path>.*)$", static.serve, {'document_root': settings.BASE_DIR / f"modules/{mod}/{setup['setup'][mod]}"})
        except Exception as e:
            continue
            # print('module does not have any urls',e)
        # spec = importlib.util.spec_from_file_location(script, f"{folder_path}/{script}")
        # script_module = importlib.util.module_from_spec(spec)
        # loaded_module = spec.loader.exec_module(script_module)    
       
# print('all urls',urlpatterns)    
