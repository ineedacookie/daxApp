from django.urls import path

from . import views

urlpatterns = [
    path('feedback/', views.add_feedback, name='add_feedback'),
]
