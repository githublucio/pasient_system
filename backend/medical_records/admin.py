from django.contrib import admin
from .models import Room, Diagnosis, DiagnosisCategory, Visit


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'order')
    search_fields = ('name', 'code')


@admin.register(DiagnosisCategory)
class DiagnosisCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'diagnosis_count')
    search_fields = ('name',)

    def diagnosis_count(self, obj):
        return obj.diagnoses.count()
    diagnosis_count.short_description = 'Total Diagnoses'


@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category')
    list_filter = ('category',)
    search_fields = ('code', 'name')


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('visit_date', 'patient', 'doctor', 'queue_number', 'patient_type', 'status')
    list_filter = ('status', 'patient_type', 'visit_date')
    search_fields = ('patient__full_name', 'patient__patient_id')
    raw_id_fields = ('patient',)
