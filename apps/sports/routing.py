from django.urls import path
from .consumers import LiveScoreConsumer

websocket_urlpatterns = [
    path('ws/live/', LiveScoreConsumer.as_asgi()),
]