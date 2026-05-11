from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_patient, name='register_patient'),
    path('hiv-register/', views.hiv_register_patient, name='hiv_register_patient'),
    path('hiv-report/', views.hiv_report_dashboard, name='hiv_report_dashboard'),
    path('edit/<uuid:uuid>/', views.edit_patient, name='edit_patient'),
    path('dashboard/<uuid:uuid>/', views.patient_dashboard, name='patient_dashboard'),
    path('reception/', views.reception_dashboard, name='reception'),
    path('check-in/<uuid:uuid>/', views.check_in_patient, name='check_in_patient'),
    path('ticket/<uuid:visit_uuid>/', views.queue_ticket, name='queue_ticket'),
    path('queue-display/', views.queue_display, name='queue_display'),

    # Master Data
    path('master/', views.master_data_dashboard, name='master_data_dashboard'),
    path('master/patients/', views.PatientListView.as_view(), name='patient_list'),
    path('master/patients/delete/<uuid:pk>/', views.PatientDeleteView.as_view(), name='patient_delete'),
    
    path('master/municipio/', views.MunicipioListView.as_view(), name='municipio_list'),
    path('master/municipio/detail/<int:pk>/', views.MunicipioDetailView.as_view(), name='municipio_detail'),
    path('master/municipio/add/', views.MunicipioCreateView.as_view(), name='municipio_add'),
    path('master/municipio/edit/<int:pk>/', views.MunicipioUpdateView.as_view(), name='municipio_edit'),
    path('master/municipio/delete/<int:pk>/', views.MunicipioDeleteView.as_view(), name='municipio_delete'),

    path('master/posto/', views.PostoListView.as_view(), name='posto_list'),
    path('master/posto/detail/<int:pk>/', views.PostoDetailView.as_view(), name='posto_detail'),
    path('master/posto/add/', views.PostoCreateView.as_view(), name='posto_add'),
    path('master/posto/edit/<int:pk>/', views.PostoUpdateView.as_view(), name='posto_edit'),
    path('master/posto/delete/<int:pk>/', views.PostoDeleteView.as_view(), name='posto_delete'),

    path('master/suco/', views.SucoListView.as_view(), name='suco_list'),
    path('master/suco/detail/<int:pk>/', views.SucoDetailView.as_view(), name='suco_detail'),
    path('master/suco/add/', views.SucoCreateView.as_view(), name='suco_add'),
    path('master/suco/edit/<int:pk>/', views.SucoUpdateView.as_view(), name='suco_edit'),
    path('master/suco/delete/<int:pk>/', views.SucoDeleteView.as_view(), name='suco_delete'),

    path('master/aldeia/', views.AldeiaListView.as_view(), name='aldeia_list'),
    path('master/aldeia/detail/<int:pk>/', views.AldeiaDetailView.as_view(), name='aldeia_detail'),
    path('master/aldeia/add/', views.AldeiaCreateView.as_view(), name='aldeia_add'),
    path('master/aldeia/edit/<int:pk>/', views.AldeiaUpdateView.as_view(), name='aldeia_edit'),
    path('master/aldeia/delete/<int:pk>/', views.AldeiaDeleteView.as_view(), name='aldeia_delete'),

    # APIs
    path('api/check-duplicates/', views.check_duplicates, name='api_check_duplicates'),
    path('api/patient-search/', views.api_patient_search, name='api_patient_search'),
    path('ajax/load-postos/', views.load_postos, name='load_postos'),
    path('ajax/load-sucos/', views.load_sucos, name='load_sucos'),
    path('ajax/load-aldeias/', views.load_aldeias, name='load_aldeias'),
]
