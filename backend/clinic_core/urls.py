"""
URL configuration for clinic_core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path
from django.views.static import serve
from patients import views as patient_views
from staff import views as staff_views
from clinic_core import views as core_views

urlpatterns = [
    # APIs outside of auth requirements

    path('api/load-postos/', patient_views.load_postos, name='load_postos'),
    path('api/load-sucos/', patient_views.load_sucos, name='load_sucos'),
    path('api/load-aldeias/', patient_views.load_aldeias, name='load_aldeias'),
    
    path('admin/', admin.site.urls),
    # Custom Logout handling (GET support)
    path('accounts/logout/', staff_views.custom_logout, name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', core_views.main_dashboard, name='main_dashboard'),
    path('patients/', include('patients.urls')),
    path('records/', include('medical_records.urls')),
    path('printing/', include('printing.urls')),
    path('staff/', include('staff.urls')),
    path('lab/', include('laboratory.urls')),
    path('pharmacy/', include('pharmacy.urls')),
    path('appointments/', include('appointments.urls')),
    path('billing/', include('billing.urls')),
    path('radiology/', include('radiology.urls')),
    path('pathology/', include('pathology.urls')),
    path('settings/', include('administration.urls')),
]

# Always serve media files, even when DEBUG is False, since we are using 
# Waitress on Windows without Nginx for this internal clinic system.
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
]

if settings.DEBUG:
    # Static files are handled by WhiteNoise in production, but we keep this 
    # for development server just in case.
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
