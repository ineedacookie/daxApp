from django.urls import path
from users import consumers

websocket_urlpatterns = [
    path('ws/', consumers.NotificationConsumer.as_asgi()),
]