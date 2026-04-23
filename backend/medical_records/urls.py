from django.urls import path
from . import views

urlpatterns = [
    path('doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('emergency/', views.emergency_dashboard, name='emergency_dashboard'),
    path('emergency/direct-registration/', views.emergency_direct_registration, name='emergency_direct_registration'),
    path('emergency/triage/', views.emergency_triage_dashboard, name='emergency_triage_dashboard'),
    path('emergency/triage/input/<uuid:visit_uuid>/', views.emergency_triage_input, name='emergency_triage_input'),
    path('triage/', views.triage_dashboard, name='triage_dashboard'),
    path('triage/input/<uuid:visit_uuid>/', views.triage_input, name='triage_input'),
    path('examination/<uuid:visit_uuid>/', views.perform_examination, name='perform_examination'),
    path('emergency/observation/<uuid:visit_uuid>/', views.record_emergency_observation, name='record_emergency_observation'),
    path('emergency/medication/<uuid:visit_uuid>/', views.administer_emergency_medication, name='administer_emergency_medication'),
    path('visit/<uuid:visit_uuid>/', views.visit_detail, name='visit_detail'),
    path('visit/ajax/<uuid:visit_uuid>/', views.visit_detail_ajax, name='visit_detail_ajax'),
    path('history/', views.department_completed_list, name='department_completed_list'),
    path('history/export/pdf/', views.export_visit_history_pdf, name='export_visit_history_pdf'),
    path('history/export/excel/', views.export_visit_history_excel, name='export_visit_history_excel'),
    path('visit/<uuid:visit_uuid>/pdf/', views.visit_summary_pdf, name='visit_summary_pdf'),
    path('reports/staff/', views.staff_performance_report, name='staff_performance_report'),
    path('reports/disease/', views.disease_statistics_report, name='disease_statistics_report'),
    path('ajax/diagnosis-search/', views.search_diagnosis_ajax, name='search_diagnosis_ajax'),
    path('completed/', views.department_completed_list, name='department_completed_list'),

    # Room Master Data
    path('master/room/', views.RoomListView.as_view(), name='room_list'),
    path('master/room/detail/<int:pk>/', views.RoomDetailView.as_view(), name='room_detail'),
    path('master/room/add/', views.RoomCreateView.as_view(), name='room_add'),
    path('master/room/edit/<int:pk>/', views.RoomUpdateView.as_view(), name='room_edit'),
    path('master/room/delete/<int:pk>/', views.RoomDeleteView.as_view(), name='room_delete'),

    # ICD-10 Master Data
    path('master/diagnosis/', views.DiagnosisListView.as_view(), name='diagnosis_list'),
    path('master/diagnosis/export/pdf/', views.export_diagnoses_pdf, name='diagnosis_export_pdf'),
    path('master/diagnosis/export/excel/', views.export_diagnoses_excel, name='diagnosis_export_excel'),
    path('master/diagnosis/detail/<int:pk>/', views.DiagnosisDetailView.as_view(), name='diagnosis_detail'),
    path('master/diagnosis/add/', views.DiagnosisCreateView.as_view(), name='diagnosis_add'),
    path('master/diagnosis/edit/<int:pk>/', views.DiagnosisUpdateView.as_view(), name='diagnosis_edit'),
    path('master/diagnosis/delete/<int:pk>/', views.DiagnosisDeleteView.as_view(), name='diagnosis_delete'),
    path('kia/direct-registration/', views.kia_direct_registration, name='kia_direct_registration'),
]
