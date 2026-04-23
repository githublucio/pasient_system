from django.urls import path
from . import views

urlpatterns = [
    path('', views.appointment_calendar, name='appointment_calendar'),
    path('create/', views.appointment_create, name='appointment_create'),
    path('<uuid:uuid>/edit/', views.appointment_edit, name='appointment_edit'),
    path('<uuid:uuid>/cancel/', views.appointment_cancel, name='appointment_cancel'),
    path('<uuid:uuid>/status/', views.appointment_status_update, name='appointment_status_update'),
    path('<uuid:uuid>/check-in-visit/', views.appointment_check_in_visit, name='appointment_check_in_visit'),
    path('hiv/', views.hiv_appointment_calendar, name='hiv_appointment_calendar'),
]
