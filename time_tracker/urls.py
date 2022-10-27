from django.urls import path

from . import views

urlpatterns = [
    path('simple_clock/', views.simple_clock, name='simple_clock'),
]
