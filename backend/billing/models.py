import uuid
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.utils import timezone
from medical_records.models import Visit
from patients.models import Patient


class ServiceCategory(models.Model):
    name = models.CharField(_('Category Name'), max_length=100)
    code = models.CharField(_('Code'), max_length=20, unique=True)
    icon = models.CharField(_('Icon CSS Class'), max_length=50, blank=True, default='bi-tag')
    order = models.PositiveIntegerField(_('Display Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('Service Category')
        verbose_name_plural = _('Service Categories')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class ServicePrice(models.Model):
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name='services', verbose_name=_('Category'))
    name = models.CharField(_('Service Name'), max_length=200)
    code = models.CharField(_('Code'), max_length=50, unique=True, blank=True, null=True)
    price = models.DecimalField(_('Price (USD)'), max_digits=10, decimal_places=2, default=0.00)
    description = models.TextField(_('Description'), blank=True, null=True)
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Service Price')
        verbose_name_plural = _('Service Prices')
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} - ${self.price}"


class InvoiceQuerySet(models.QuerySet):
    def visible_to(self, user):
        if user.is_superuser:
            return self
        
        is_hiv_staff = False
        staff_profile = getattr(user, 'staff_profile', None)
        if staff_profile:
            try:
                dept_code = staff_profile.department.code.upper()
                is_hiv_staff = dept_code in ['HIV', 'AIDS']
            except AttributeError:
                pass
        
        if is_hiv_staff:
            return self
        return self.filter(patient__is_hiv_patient=False)

class InvoiceManager(models.Manager):
    def get_queryset(self):
        return InvoiceQuerySet(self.model, using=self._db)
    
    def visible_to(self, user):
        return self.get_queryset().visible_to(user)

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('UNPAID', _('Unpaid')),
        ('PAID', _('Paid')),
        ('PARTIAL', _('Partially Paid')),
        ('CANCELLED', _('Cancelled')),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('CASH', _('Cash')),
        ('CARD', _('Card')),
        ('TRANSFER', _('Bank Transfer')),
        ('OTHER', _('Other')),
    ]

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(_('Invoice Number'), max_length=30, unique=True, db_index=True)
    visit = models.OneToOneField(Visit, on_delete=models.PROTECT, related_name='invoice', verbose_name=_('Visit'), blank=True, null=True)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='invoices', verbose_name=_('Patient'))

    subtotal = models.DecimalField(_('Subtotal'), max_digits=12, decimal_places=2, default=0.00)
    discount = models.DecimalField(_('Discount (USD)'), max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(_('Total Amount (USD)'), max_digits=12, decimal_places=2, default=0.00)
    amount_paid = models.DecimalField(_('Amount Paid (USD)'), max_digits=12, decimal_places=2, default=0.00)

    status = models.CharField(_('Status'), max_length=15, choices=STATUS_CHOICES, default='UNPAID')
    payment_method = models.CharField(_('Payment Method'), max_length=15, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    notes = models.TextField(_('Notes'), blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_invoices', verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    paid_at = models.DateTimeField(_('Paid At'), blank=True, null=True)

    objects = InvoiceManager()

    class Meta:
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at'], name='idx_invoice_created'),
            models.Index(fields=['patient', '-created_at'], name='idx_invoice_patient'),
            models.Index(fields=['status'], name='idx_invoice_status'),
            GinIndex(name='idx_invoice_num_trgm', fields=['invoice_number'], opclasses=['gin_trgm_ops']),
        ]
        permissions = [
            ("view_menu_billing", "Can see Billing menu in sidebar"),
            ("can_export_invoices", "Can export invoice data"),
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.patient.full_name}"

    @property
    def balance_due(self):
        return max(self.total_amount - self.amount_paid, 0)

    def get_items_summary(self, max_length=500, separator='; '):
        """Line-item descriptions for payments, reports, and receipts (not only invoice number)."""
        parts = []
        for item in self.items.all().order_by('pk'):
            d = (item.description or '').strip()
            if not d:
                continue
            cat_name = None
            if getattr(item, 'category_id', None) and item.category:
                cat_name = item.category.name
            elif getattr(item, 'service_id', None) and item.service and getattr(item.service, 'category_id', None):
                cat_name = item.service.category.name
            if cat_name:
                parts.append(f'{d} ({cat_name})')
            else:
                parts.append(d)
        text = separator.join(parts)
        if not text:
            return ''
        if max_length and len(text) > max_length:
            return text[: max_length - 1].rstrip() + '…'
        return text

    def recalculate(self):
        from django.db.models import Sum, F
        agg = self.items.aggregate(total=Sum(F('quantity') * F('unit_price')))
        self.subtotal = agg['total'] or 0
        # FIX RISK #4: Cap discount so it never exceeds subtotal.
        # Prevents storing inconsistent data (e.g. discount=$1000 on a $5 bill).
        if self.discount > self.subtotal:
            self.discount = self.subtotal
        self.total_amount = max(self.subtotal - self.discount, 0)
        if self.amount_paid >= self.total_amount and self.total_amount > 0:
            self.status = 'PAID'
            if not self.paid_at:
                self.paid_at = timezone.now()
        elif self.amount_paid > 0:
            self.status = 'PARTIAL'
        else:
            self.status = 'UNPAID'
        self.save()

    @classmethod
    def create_next(cls, **kwargs):
        """FIX BUG #2: Thread-safe invoice creation with atomic sequential numbering.
        Generates the invoice number AND creates the record within a single
        transaction.atomic() + select_for_update() block, eliminating the race
        condition that existed between the old generate_invoice_number() call
        and the subsequent objects.create() call.
        """
        from django.db import transaction
        with transaction.atomic():
            today = timezone.localdate()
            prefix = f"INV-{today.strftime('%Y%m%d')}"
            last = cls.objects.select_for_update().filter(
                invoice_number__startswith=prefix
            ).order_by('-invoice_number').first()
            if last:
                try:
                    last_seq = int(last.invoice_number.split('-')[-1])
                except (ValueError, IndexError):
                    last_seq = 0
                seq = last_seq + 1
            else:
                seq = 1
            invoice_number = f"{prefix}-{seq:04d}"
            return cls.objects.create(invoice_number=invoice_number, **kwargs)

    @staticmethod
    def generate_invoice_number():
        """Deprecated: Use Invoice.create_next(**kwargs) instead.
        Kept for backwards compatibility only.
        """
        today = timezone.localdate()
        prefix = f"INV-{today.strftime('%Y%m%d')}"
        last = Invoice.objects.filter(invoice_number__startswith=prefix).order_by('-invoice_number').first()
        if last:
            try:
                last_seq = int(last.invoice_number.split('-')[-1])
            except (ValueError, IndexError):
                last_seq = 0
            seq = last_seq + 1
        else:
            seq = 1
        return f"{prefix}-{seq:04d}"


class InvoiceItem(models.Model):
    ITEM_TYPE_CHOICES = [
        ('SERVICE', _('Service / Consultation')),
        ('MEDICINE', _('Medicine / Pharmacy')),
        ('LAB', _('Laboratory Test')),
        ('OTHER', _('Other')),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items', verbose_name=_('Invoice'))
    item_type = models.CharField(_('Item Type'), max_length=10, choices=ITEM_TYPE_CHOICES, default='SERVICE')
    
    # FKs for integrated items
    service = models.ForeignKey(ServicePrice, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Service'))
    from pharmacy.models import Medicine
    medicine = models.ForeignKey('pharmacy.Medicine', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Medicine'))
    
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Category'))
    description = models.CharField(_('Description'), max_length=255)
    quantity = models.PositiveIntegerField(_('Quantity'), default=1)
    unit_price = models.DecimalField(_('Unit Price (USD)'), max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        verbose_name = _('Invoice Item')
        verbose_name_plural = _('Invoice Items')

    def __str__(self):
        return f"[{self.get_item_type_display()}] {self.description} x{self.quantity}"

    @property
    def line_total(self):
        return self.quantity * self.unit_price


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = Invoice.PAYMENT_METHOD_CHOICES

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments', verbose_name=_('Invoice'))
    amount = models.DecimalField(_('Amount (USD)'), max_digits=12, decimal_places=2)
    payment_method = models.CharField(_('Payment Method'), max_length=15, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    reference = models.CharField(_('Reference / Receipt No'), max_length=100, blank=True, null=True)
    notes = models.TextField(_('Notes'), blank=True, null=True)
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_('Received By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment ${self.amount} for {self.invoice.invoice_number}"
