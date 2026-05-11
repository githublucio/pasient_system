from django.contrib import admin
from .models import Medicine, Prescription, DispensedItem, StockBatch, PrescriptionItem


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'unit', 'total_stock', 'min_stock', 'is_low_stock', 'is_active')
    list_filter = ('unit', 'is_active', 'department_category')
    search_fields = ('name', 'code')
    list_editable = ('min_stock', 'is_active')


class DispensedItemInline(admin.TabularInline):
    model = DispensedItem
    extra = 0
    readonly_fields = ('dispensed_at',)


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('visit', 'date_created', 'has_allergy', 'doctor', 'dispensing_status', 'dispensed_by')
    list_filter = ('has_allergy', 'dispensing_status', 'date_created')
    search_fields = ('visit__patient__full_name', 'allergy_medicine', 'prescription_text')
    inlines = [DispensedItemInline]


@admin.register(StockBatch)
class StockBatchAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'batch_number', 'expiry_date', 'quantity_received', 'quantity_remaining', 'source_type', 'purchase_date', 'unit_price', 'is_expired')
    list_filter = ('source_type', 'purchase_date', 'expiry_date', 'medicine')
    search_fields = ('medicine__name', 'batch_number', 'supplier', 'donor_name')
    date_hierarchy = 'purchase_date'

