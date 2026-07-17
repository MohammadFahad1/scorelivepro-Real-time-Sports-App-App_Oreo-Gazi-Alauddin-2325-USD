# config/asgi.py
import os
from django.core.asgi import get_asgi_application

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Import directly from 'sports', REMOVING 'apps.' prefix
from sports.routing import websocket_urlpatterns 

application = ProtocolTypeRouter({
    # Django's ASGI application to handle traditional HTTP requests
    "http": django_asgi_app,

    # WebSocket handler
    # We purposefully do NOT use AllowedHostsOriginValidator here to allow
    # mobile apps and Postman to connect easily. 
    # Production security is handled by Nginx and ALLOWED_HOSTS in settings.
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})