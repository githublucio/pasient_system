from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.radiology_dashboard, name='radiology_dashboard'),
    path('request/<uuid:visit_uuid>/', views.radiology_request_create, name='radiology_request_create'),
    path('result/<uuid:request_uuid>/', views.radiology_result_input, name='radiology_result_input'),
]

