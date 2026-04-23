from django.contrib import admin
from .models import Municipio, PostoAdministrativo, Suco, Aldeia, Patient, DailyQueue, PatientID


class PatientIDInline(admin.TabularInline):
    model = PatientID
    extra = 1
    fields = ('id_type', 'id_number')


class PostoInline(admin.TabularInline):
    model = PostoAdministrativo
    extra = 1


class SucoInline(admin.TabularInline):
    model = Suco
    extra = 1


class AldeiaInline(admin.TabularInline):
    model = Aldeia
    extra = 1


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    inlines = [PostoInline]


@admin.register(PostoAdministrativo)
class PostoAdminAdmin(admin.ModelAdmin):
    list_display = ['name', 'municipio']
    list_filter = ['municipio']
    search_fields = ['name']
    inlines = [SucoInline]


@admin.register(Suco)
class SucoAdmin(admin.ModelAdmin):
    list_display = ['name', 'posto', 'get_municipio']
    list_filter = ['posto__municipio', 'posto']
    search_fields = ['name']
    inlines = [AldeiaInline]

    def get_municipio(self, obj):
        return obj.posto.municipio.name
    get_municipio.short_description = 'Municipio'


@admin.register(Aldeia)
class AldeiaAdmin(admin.ModelAdmin):
    list_display = ['name', 'suco', 'get_posto', 'get_municipio']
    list_filter = ['suco__posto__municipio', 'suco__posto', 'suco']
    search_fields = ['name']

    def get_posto(self, obj):
        return obj.suco.posto.name
    get_posto.short_description = 'Posto'

    def get_municipio(self, obj):
        return obj.suco.posto.municipio.name
    get_municipio.short_description = 'Municipio'


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['patient_id', 'full_name', 'gender', 'patient_category', 'municipio', 'suco']
    search_fields = ['full_name', 'patient_id']
    list_filter = ['patient_category', 'gender', 'municipio']
    inlines = [PatientIDInline]


@admin.register(DailyQueue)
class DailyQueueAdmin(admin.ModelAdmin):
    list_display = ['date', 'department', 'current_number']
