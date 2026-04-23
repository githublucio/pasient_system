from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.lab_dashboard, name='lab_dashboard'),
    path('request/<uuid:visit_uuid>/', views.lab_request_create, name='lab_request_create'),
    path('result/<uuid:request_uuid>/', views.lab_result_input, name='lab_result_input'),
]
