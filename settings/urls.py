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
from scripts import login, queues


print(pylims.term(),"Starting Pylims Server v1.1")

urlpatterns = [
    path('', views.home, name="home"),
    path('login/',views.show_login, name='show_login'),
    path('setup/', views.setup, name="setup"),
    path('setup_save/', views.setup_save, name="setup_save"),
    path('login_submit/', login.login_submit, name="login_submit"),
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

]
