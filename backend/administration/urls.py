from django.urls import path
from . import views

urlpatterns = [
    path('', views.backup_restore_view, name='backup_restore'),
    path('backup/', views.backup_database, name='backup_database'),
    path('restore/', views.restore_database, name='restore_database'),
    path('dashboard/geo/', views.geographical_dashboard, name='geo_dashboard'),
]
