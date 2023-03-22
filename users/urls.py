from django.urls import path, re_path

from . import views
from . import consumers

urlpatterns = [
    re_path(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,40})/$', views.activate_account,
            name='activate'),
]

urlpatterns += [
    path('', views.home, name='home'),
    path('landing/', views.landing_page, name="landing_page"),
    path('register/', views.register_account, name="register"),
    path('company_settings/', views.company_settings, name="company_settings"),
    path('selectable_employees', views.selectable_employees, name="selectable_employees"),
    # path('dashboard/', views.dashboard, name="dashboard"),
    # path('admin/company_settings/', views.company_settings, name="company_settings"),
    # path('admin/create_employee/', views.create_employee, name="create_employee"),
    # path('admin/send_confirmation_email/<int:employee_id>/', views.send_confirmation_email, name='send_confirmation_email'),
    # path('admin/employee/<int:employee_id>/', views.edit_employee, name="edit_employee"),
    # path('admin/employee/<int:employee_id>/delete/', views.delete_employee, name="delete_employee"),
    # path('admin/change_employee_password/<int:employee_id>/', views.admin_change_password, name='change_employee_password'),
    # path('account_settings/', views.edit_account_settings, name='account_settings'),
    # path('change_password/', views.change_password, name='change_password'),
]
