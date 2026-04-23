from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.pharmacy_dashboard, name='pharmacy_dashboard'),
    path('prescription/<uuid:visit_uuid>/', views.prescription_create, name='prescription_create'),
    path('dispense/<uuid:prescription_uuid>/', views.pharmacy_dispense, name='pharmacy_dispense'),

    # Medicine CRUD
    path('medicines/', views.medicine_list, name='medicine_list'),
    path('medicines/add/', views.medicine_add, name='medicine_add'),
    path('medicines/edit/<int:pk>/', views.medicine_edit, name='medicine_edit'),
    path('medicines/delete/<int:pk>/', views.medicine_delete, name='medicine_delete'),

    # Stock Entry CRUD
    path('stock/', views.stock_entry_list, name='stock_entry_list'),
    path('stock/add/', views.stock_entry_add, name='stock_entry_add'),
    path('stock/edit/<int:pk>/', views.stock_entry_edit, name='stock_entry_edit'),
    path('stock/delete/<int:pk>/', views.stock_entry_delete, name='stock_entry_delete'),
]
