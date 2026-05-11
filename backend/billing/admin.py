from django.contrib import admin
from .models import ServiceCategory, ServicePrice, Invoice, InvoiceItem, Payment


class ServicePriceInline(admin.TabularInline):
    model = ServicePrice
    extra = 1


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'order', 'is_active')
    inlines = [ServicePriceInline]


@admin.register(ServicePrice)
class ServicePriceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'code')


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'patient', 'total_amount', 'amount_paid', 'status', 'created_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('invoice_number', 'patient__full_name', 'patient__patient_id')
    inlines = [InvoiceItemInline, PaymentInline]

    def save_model(self, request, obj, form, change):
        """FIX #1: Recalculate invoice totals when discount or metadata is
        edited directly via the Django admin panel."""
        super().save_model(request, obj, form, change)
        obj.recalculate()

    def save_formset(self, request, form, formset, change):
        """FIX #1: Recalculate invoice totals after any inline (InvoiceItem
        or Payment) is added, edited, or deleted via the Django admin panel.
        Also re-sums amount_paid from the payments table so payment edits
        are reflected correctly before recalculate() runs.
        """
        super().save_formset(request, form, formset, change)
        invoice = form.instance
        if not hasattr(invoice, 'recalculate'):
            return
        from django.db.models import Sum
        invoice.amount_paid = invoice.payments.aggregate(
            total=Sum('amount')
        )['total'] or 0
        invoice.recalculate()


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount', 'payment_method', 'received_by', 'created_at')
    list_filter = ('payment_method',)
