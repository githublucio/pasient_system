from django.contrib import admin
from .models import LabTest, LabRequest, LabResult

@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'column_index', 'order')
    list_filter = ('column_index',)
    search_fields = ('name', 'code')
    ordering = ('column_index', 'order', 'name')

@admin.register(LabRequest)
class LabRequestAdmin(admin.ModelAdmin):
    list_display = ('visit', 'date_of_request', 'patient_type', 'urgency', 'requesting_physician')
    list_filter = ('patient_type', 'urgency', 'special_category', 'date_of_request')
    search_fields = ('visit__patient__full_name', 'lab_no', 'visit__patient__patient_id')
    filter_horizontal = ('tests',)


@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display = ('lab_request', 'verified_by', 'completed_at', 'created_at')
    list_filter = ('completed_at',)
    search_fields = ('lab_request__visit__patient__full_name',)
