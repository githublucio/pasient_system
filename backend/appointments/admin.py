from django.contrib import admin
from .models import Appointment

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'appointment_date', 'appointment_time', 'department', 'doctor', 'status']
    list_filter = ['status', 'appointment_date', 'department']
    search_fields = ['patient__full_name', 'patient__patient_id']
    raw_id_fields = ['patient', 'doctor']
