from django.urls import path

from . import views

urlpatterns = [
    path('admin/reports/', views.reports, name='admin_reports'),
    path('employee/reports/', views.employee_reports, name='employee_reports'),
    path('admin/modify_times/', views.modify_times_emp_list, name="admin_modify_times_emp_list"),
    path('admin/modify_times/<int:employee_id>/', views.modify_times_table, name="admin_modify_times_table"),
    # Makes selected date optional
    path('admin/modify_times/<int:employee_id>/<str:selected_date>/', views.modify_times_table,
         name="admin_modify_times_table"),
    path('admin/time_action_create/<int:employee_id>/', views.create_time_action,
         name="admin_create_today_time_action"),
    path('admin/time_action_create/<int:employee_id>/<str:selected_date>/', views.create_time_action,
         name="admin_create_time_action"),
    path('admin/time_action_edit/<int:time_action_id>/', views.edit_time_action, name="admin_edit_time_action"),
    path('admin/time_action/<int:time_action_id>/delete/', views.delete_time_action,
         name="admin_delete_time_action"),
]
