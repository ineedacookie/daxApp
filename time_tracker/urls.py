from django.urls import path

from . import views

urlpatterns = [
    path('simple_clock/', views.simple_clock, name='simple_clock'),
    path('manage_times/', views.manage_times, name='manage_times'),
    path('manage_times/event/', views.event_handler, name='manage_time_event'),
    path('get_time_actions', views.fetch_actions, name='get_time_actions'),
    path('delete_action', views.delete_action, name='delete_action'),
    path('report_center/', views.report_center, name='report_center')
]
