from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.pathology_dashboard, name='pathology_dashboard'),
    path('request/<uuid:visit_uuid>/', views.pathology_request_create, name='pathology_request_create'),
    path('result/<uuid:request_uuid>/', views.pathology_result_input, name='pathology_result_input'),
]

