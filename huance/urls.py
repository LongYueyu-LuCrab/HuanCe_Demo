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
from django.urls import path, re_path
from core.views import add_employee, create_order, current_user, download_order_document, frontend, lab_device_availability, lab_device_detail, lab_devices, laboratory_orders, laboratory_orders_export, lims_action, lims_dashboard, lims_login, lims_logout, order_detail

urlpatterns = [
    path('', frontend, name='frontend'),
    path('api/auth/me/', current_user, name='current_user'),
    path('api/auth/login/', lims_login, name='lims_login'),
    path('api/auth/logout/', lims_logout, name='lims_logout'),
    path('api/employees/add/', add_employee, name='add_employee'),
    path('api/orders/create/', create_order, name='create_order'),
    path('api/orders/<str:order_no>/', order_detail, name='order_detail'),
    path('api/orders/documents/<int:document_id>/download/', download_order_document, name='download_order_document'),
    path('api/labs/devices/', lab_devices, name='lab_devices'),
    path('api/labs/devices/availability/', lab_device_availability, name='lab_device_availability'),
    path('api/labs/devices/<int:device_id>/', lab_device_detail, name='lab_device_detail'),
    path('api/labs/orders/', laboratory_orders, name='laboratory_orders'),
    path('api/labs/orders/export/', laboratory_orders_export, name='laboratory_orders_export'),
    path('api/lims/action/', lims_action, name='lims_action'),
    path('api/lims/dashboard/', lims_dashboard, name='lims_dashboard'),
    path('admin/', admin.site.urls),
    re_path(r'^(?!api/|admin/|static/).*$', frontend, name='frontend_spa'),
]
