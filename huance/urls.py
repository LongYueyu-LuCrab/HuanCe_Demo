"""
URL configuration for huance project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.urls import path
from core.views import add_employee, create_order, current_user, frontend, lims_dashboard, lims_login, lims_logout

urlpatterns = [
    path('', frontend, name='frontend'),
    path('api/auth/me/', current_user, name='current_user'),
    path('api/auth/login/', lims_login, name='lims_login'),
    path('api/auth/logout/', lims_logout, name='lims_logout'),
    path('api/employees/add/', add_employee, name='add_employee'),
    path('api/orders/create/', create_order, name='create_order'),
    path('api/lims/dashboard/', lims_dashboard, name='lims_dashboard'),
    path('admin/', admin.site.urls),
]
