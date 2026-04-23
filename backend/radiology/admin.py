from django.contrib import admin
from .models import RadiologyTest, RadiologyRequest, RadiologyResult

@admin.register(RadiologyTest)
class RadiologyTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    ordering = ('order', 'name')

@admin.register(RadiologyRequest)
class RadiologyRequestAdmin(admin.ModelAdmin):
    list_display = ('visit', 'date_of_request', 'status', 'requesting_physician')
    list_filter = ('status', 'date_of_request')
    search_fields = ('visit__patient__full_name',)
    filter_horizontal = ('tests',)

@admin.register(RadiologyResult)
class RadiologyResultAdmin(admin.ModelAdmin):
    list_display = ('radiology_request', 'verified_by', 'completed_at', 'created_at')
    list_filter = ('completed_at',)
    search_fields = ('radiology_request__visit__patient__full_name',)
