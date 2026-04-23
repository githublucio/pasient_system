from django.contrib import admin
from .models import PathologyTest, PathologyRequest, PathologyResult

@admin.register(PathologyTest)
class PathologyTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    ordering = ('order', 'name')

@admin.register(PathologyRequest)
class PathologyRequestAdmin(admin.ModelAdmin):
    list_display = ('visit', 'date_of_request', 'status', 'requesting_physician', 'billing_type')
    list_filter = ('status', 'billing_type', 'date_of_request')
    search_fields = ('visit__patient__full_name',)
    filter_horizontal = ('tests',)

@admin.register(PathologyResult)
class PathologyResultAdmin(admin.ModelAdmin):
    list_display = ('pathology_request', 'verified_by', 'completed_at', 'created_at')
    list_filter = ('completed_at',)
    search_fields = ('pathology_request__visit__patient__full_name',)
