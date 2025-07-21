"""
ASGI config for src project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
from channels.middleware import BaseMiddleware
from channels.sessions import SessionMiddlewareStack
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
from settings.channels import automation_configure, projects



os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.settings")

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket":SessionMiddlewareStack( 
        URLRouter([
                path("ws/automation/", automation_configure.as_asgi()),
                path("ws/projects/", projects.as_asgi()),
            ]))
            ,
        })
