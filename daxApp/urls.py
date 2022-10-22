"""daxApp URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
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
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'Imperial Officer'
admin.site.site_title = 'Officer Site Admin'

urlpatterns = [
    path('io_admin/', admin.site.urls),
    path('io_admin/log_viewer/', include('log_viewer.urls')),
]

# Add django site authenticated urls (for login, logout, password management)
urlpatterns += [
    path('', include('django.contrib.auth.urls')),
]

# Add user create app
urlpatterns += [
    path('', include('users.urls')),
]

# Add feedback module
urlpatterns += [
    path('', include('feedback.urls'))
]

handler404 = 'users.views.handler404'
handler500 = 'users.views.handler500'