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
from scripts import login, queues, steps, samples, specimens, user_scripts, logout, roles, assays, containers


print(pylims.term(),"Starting Pylims Server v1.1")

urlpatterns = [
    path('', views.home, name="home"),
    path('login/',views.show_login, name='show_login'),
    path('login/<str:code>', views.login_with_code, name='login_with_code'),
    path('enter_activation_code/', views.enter_activation_code, name='enter_activation_code'),
    path('activate_account/', views.activate_account, name='activate_account'),
    path('resend_activation_code/', views.resend_activation_code, name='resend_activation_code'),
    path('logout/', views.show_logout, name='show_logout'),
    path('login_submit/', login.login_submit, name="login_submit"),
    path('logout_submit/', logout.logout_submit, name="submit"),
    path('view_settings/', views.view_settings, name="view_settings"),
    path('settings_operators/', views.settings_operators, name="settings_operators"),
    path('settings_roles/', roles.settings_roles, name="settings_roles"),
    path('settings_assays/', assays.settings_assays, name="settings_assays"),
    
    #roles
    path('save_role/', roles.save_role, name="save_role"),
    path('edit_role/', roles.edit_role, name="edit_role"),
    path('delete_role/', roles.delete_role, name="delete_role"),
    path('assign_user_roles/', roles.assign_user_roles, name="assign_user_roles"),
    path('get_user_roles/', roles.get_user_roles, name="get_user_roles"),
    path('get_all_users/', roles.get_all_users, name="get_all_users"),
    path('get_all_roles/', roles.get_all_roles, name="get_all_roles"),
    path('create_account/', roles.create_account, name="create_account"),

    #assays
    path('save_assay/', assays.save_assay, name="save_assay"),
    path('create_assay/', assays.create_assay, name="create_assay"),
    path('get_assay_details/', assays.get_assay_details, name="get_assay_details"),
    path('archive_assay/', assays.archive_assay, name="archive_assay"),
    path('unarchive_assay/', assays.unarchive_assay, name="unarchive_assay"),
    path('create_draft_version/', assays.create_draft_version, name="create_draft_version"),
    path('save_step_order/', assays.save_step_order, name="save_step_order"),
    path('save_version_name/', assays.save_version_name, name="save_version_name"),
    path('get_step_config/', assays.get_step_config, name="get_step_config"),
    path('save_step_config/', assays.save_step_config, name="save_step_config"),
    path('get_special_samples/', assays.get_special_samples, name="get_special_samples"),
    path('settings_assay_view/<int:assay_id>/', assays.settings_assay_view, name="settings_assay_view"),
    path('settings_assay_configure/<int:assay_id>/', assays.settings_assay_configure, name="settings_assay_configure"),
    path('settings_assay_configure/<int:assay_id>/<int:step_id>/', assays.settings_assay_configure, name="settings_assay_configure_step"),

    #containers
    path('settings_containers/', containers.settings_containers, name="settings_containers"),
    path('create_container_type/', containers.create_container_type, name="create_container_type"),
    path('get_container_types/', containers.get_container_types, name="get_container_types"),
    path('get_container_type_details/', containers.get_container_type_details, name="get_container_type_details"),
    path('delete_container_type/', containers.delete_container_type, name="delete_container_type"),


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

    #specimens
    path("specimens/", specimens.display_specimens, name="display_specimens"),
    path("add_to_assay/", specimens.add_to_assay, name="add_to_assay"),

    #scripts
    path("script/run/", user_scripts.run_script, name="run_script"),
]
