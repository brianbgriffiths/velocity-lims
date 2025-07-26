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
from scripts import login, queues, steps, samples, user_scripts, logout


print(pylims.term(),"Starting Pylims Server v1.1")

urlpatterns = [
    path('', views.home, name="home"),
    path('login/',views.show_login, name='show_login'),
    path('logout/', views.show_logout, name='show_logout'),
    path('setup/', views.setup, name="setup"),
    path('setup_save/', views.setup_save, name="setup_save"),
    path('login_submit/', login.login_submit, name="login_submit"),
    path('logout_submit/', logout.logout_submit, name="submit"),
    path('view_settings/', views.view_settings, name="view_settings"),
    path('settings_operators/', views.settings_operators, name="settings_operators"),
    path('settings_roles/', views.settings_roles, name="settings_roles"),
    path('save_role/', views.save_role, name="save_role"),
    path('edit_role/', views.edit_role, name="edit_role"),
    path('delete_role/', views.delete_role, name="delete_role"),

    #queues
    path("queues/", queues.display_queues, name="display_queues"),
    path('queue/<str:queue>', queues.display_queue, name='display_queue'),
    path('reserved/<str:reserved>', queues.display_reserved, name='display_reserved'),
    path('reserve/',queues.reserve_sample, name='reserve_sample'),
    path('reserve_samples/',queues.reserve_samples, name='reserve_samples'),
    path('remove_samples/',queues.remove_samples, name='remove_samples'),
    path('release/',queues.release_sample, name='release_sample'),
    path('releaseall/',queues.release_all_samples, name='release_all_samples'),
    path('addcontrol/',queues.add_control, name='add_control'),
    path('addallcontrols/',queues.add_all_controls, name='add_all_controls'),
    path('controls/remove/',queues.remove_controls, name='remove_controls'),

    #steps
    path("steps/begin/", steps.begin_step, name="begin_step"),
    path('step/<str:step>', steps.load_step, name='load_step'),
    path('step/<str:step>/<str:page>', steps.load_step, name='load_step'),
    path('step/nextstep/', steps.next_step, name='next_step'),
    path('step/save/', steps.save_step, name='save_step'),
    path('step/saveplacements/', steps.save_placements, name='save_placements'),

    #samples
    path("samples/", samples.display_samples, name="display_samples"),
    path("add_to_assay/", samples.add_to_assay, name="add_to_assay"),

    #scripts
    path("script/run/", user_scripts.run_script, name="run_script"),
]
