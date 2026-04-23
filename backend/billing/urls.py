from django.urls import path
from . import views

urlpatterns = [
    path('', views.billing_dashboard, name='billing_dashboard'),
    path('invoice/create/', views.invoice_create, name='invoice_create'),
    path('invoice/create/visit/<uuid:visit_uuid>/', views.invoice_create_for_visit, name='invoice_create_for_visit'),
    path('invoice/<uuid:uuid>/', views.invoice_detail, name='invoice_detail'),
    path('invoice/<uuid:uuid>/print/', views.invoice_print, name='invoice_print'),
    path('invoice/<uuid:uuid>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('report/pdf/', views.billing_report_pdf, name='billing_report_pdf'),
    path('invoice/<uuid:invoice_uuid>/payment/', views.payment_create, name='payment_create'),

    # Service Price Master Data
    path('services/', views.service_category_list, name='service_category_list'),
    path('services/category/add/', views.service_category_add, name='service_category_add'),
    path('services/category/<int:pk>/edit/', views.service_category_edit, name='service_category_edit'),
    path('services/price/add/<int:category_pk>/', views.service_price_add, name='service_price_add'),
    path('services/price/<int:pk>/edit/', views.service_price_edit, name='service_price_edit'),
    path('services/price/<int:pk>/delete/', views.service_price_delete, name='service_price_delete'),

    # API
    path('api/patients/', views.api_search_patients, name='api_search_patients'),
    path('api/services/', views.api_services_by_category, name='api_services_by_category'),
    path('api/patient/<uuid:patient_uuid>/visits/', views.api_patient_visits, name='api_patient_visits'),

    # Reports
    path('report/', views.billing_report, name='billing_report'),
    path('patient/<uuid:patient_uuid>/history/', views.patient_billing_history, name='patient_billing_history'),
]
