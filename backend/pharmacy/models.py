import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.postgres.indexes import GinIndex
from medical_records.models import Visit


class Medicine(models.Model):
    UNIT_CHOICES = [
        ('TABLET', _('Tablet')),
        ('CAPSULE', _('Capsule')),
        ('BOTTLE', _('Bottle')),
        ('TUBE', _('Tube')),
        ('AMPOULE', _('Ampoule')),
        ('VIAL', _('Vial')),
        ('BAG', _('Bag / Kolf')),
        ('CYLINDER', _('Cylinder / Tabung')),
        ('SACHET', _('Sachet')),
        ('BOX', _('Box / Kotak')),
        ('ML', _('mL')),
        ('PIECE', _('Piece')),
    ]

    FORM_CHOICES = [
        ('TABLET', _('Tablet')),
        ('CAPSULE', _('Capsule')),
        ('SYRUP', _('Syrup (Xarope)')),
        ('INJECTION', _('Injection (Injeksaun)')),
        ('INFUSION', _('Infusion (Infus)')),
        ('CREAM', _('Cream/Ointment (Krema)')),
        ('DROPS', _('Drops (Tetes)')),
        ('INHALER', _('Inhaler')),
        ('SUPPOSITORY', _('Suppository')),
        ('POWDER', _('Powder (Pozolok)')),
        ('SUSPENSION', _('Suspension')),
        ('OTHER', _('Other (Seluk)')),
    ]

    name = models.CharField(_('Medicine Name'), max_length=200)
    strength = models.CharField(_('Strength / Dosage'), max_length=50, blank=True, null=True, help_text=_("e.g. 500mg, 250mg, 125mg/5ml, 10mg/ml"))
    form = models.CharField(_('Form / Sediaan'), max_length=20, choices=FORM_CHOICES, default='TABLET')
    code = models.CharField(_('Code'), max_length=50, unique=True, blank=True, null=True)
    unit = models.CharField(_('Unit'), max_length=20, choices=UNIT_CHOICES, default='TABLET')
    stock = models.PositiveIntegerField(_('Current Stock'), default=0)
    min_stock = models.PositiveIntegerField(_('Minimum Stock Alert'), default=10)
    description = models.TextField(_('Description'), blank=True, null=True)
    DEPARTMENT_CHOICES = [
        ('GENERAL', _('General Pharmacy')),
        ('HIV', _('HIV/AIDS Department')),
        ('TB', _('TB Department')),
        ('DENTAL', _('Dental Department')),
        ('KIA', _('MCH/KIA Department')),
    ]
    department_category = models.CharField(_('Department Category'), max_length=20, choices=DEPARTMENT_CHOICES, default='GENERAL')
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Medicine')
        verbose_name_plural = _('Medicines')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name'], name='idx_medicine_name'),
            GinIndex(name='idx_med_name_trgm', fields=['name'], opclasses=['gin_trgm_ops']),
            GinIndex(name='idx_med_code_trgm', fields=['code'], opclasses=['gin_trgm_ops']),
        ]

    @property
    def display_name(self):
        parts = [self.name]
        if self.strength:
            parts.append(self.strength)
        parts.append(f"({self.get_form_display()})")
        return ' '.join(parts)

    def __str__(self):
        return f"{self.display_name} - Stock: {self.stock}"

    @property
    def is_low_stock(self):
        return self.stock <= self.min_stock

    @property
    def nearest_expiry(self):
        from django.utils import timezone
        entry = self.stock_entries.filter(
            expiry_date__isnull=False, remaining_qty__gt=0
        ).order_by('expiry_date').first()
        return entry.expiry_date if entry else None

    @property
    def has_expired_stock(self):
        from django.utils import timezone
        return self.stock_entries.filter(
            expiry_date__lt=timezone.localdate(), remaining_qty__gt=0
        ).exists()


class StockEntry(models.Model):
    SOURCE_CHOICES = [
        ('PURCHASE', _('Clinic Purchase (Sosa Rasik)')),
        ('GOV_DONATION', _('Government Donation (Doasaun Governu)')),
        ('NGO_INT', _('International NGO Donation (ONG Internasional)')),
        ('NGO_NAT', _('National NGO Donation (ONG Nasional)')),
        ('VOLUNTEER', _('Volunteer Donation (Voluntariu)')),
        ('OTHER', _('Other (Seluk)')),
    ]

    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='stock_entries', verbose_name=_('Medicine'))
    source_type = models.CharField(_('Source / Origem'), max_length=20, choices=SOURCE_CHOICES, default='PURCHASE')
    donor_name = models.CharField(_('Donor / Organization Name'), max_length=255, blank=True, null=True, help_text=_("Name of donor, NGO, or government program"))
    quantity = models.PositiveIntegerField(_('Quantity Received'))
    remaining_qty = models.PositiveIntegerField(_('Remaining Quantity'))
    expiry_date = models.DateField(_('Expiry Date'), blank=True, null=True)
    batch_number = models.CharField(_('Batch Number'), max_length=100, blank=True, null=True)
    supplier = models.CharField(_('Supplier / Vendor'), max_length=200, blank=True, null=True)
    purchase_date = models.DateField(_('Received Date / Data Simu'))
    unit_price = models.DecimalField(_('Unit Price (USD)'), max_digits=10, decimal_places=2, default=0, help_text=_("Set to 0 for donations"))
    notes = models.TextField(_('Notes'), blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Stock Entry')
        verbose_name_plural = _('Stock Entries')
        ordering = ['-purchase_date', '-created_at']
        indexes = [
            GinIndex(name='idx_stock_batch_trgm', fields=['batch_number'], opclasses=['gin_trgm_ops']),
            GinIndex(name='idx_stock_supplier_trgm', fields=['supplier'], opclasses=['gin_trgm_ops']),
        ]

    def __str__(self):
        return f"{self.medicine.name} +{self.quantity} ({self.purchase_date})"

    @property
    def is_expired(self):
        from django.utils import timezone
        if self.expiry_date:
            return self.expiry_date < timezone.localdate()
        return False

    @property
    def total_cost(self):
        return self.quantity * self.unit_price


class Prescription(models.Model):
    ALLERGY_CHOICES = [
        ('IHA', _('Yes (Iha)')),
        ('LA_IHA', _('No (La Iha)')),
    ]

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='prescription', verbose_name=_('Visit'))
    
    date_created = models.DateTimeField(_('Date Created'), auto_now_add=True)
    
    has_allergy = models.CharField(_('Alerjia'), max_length=10, choices=ALLERGY_CHOICES, default='LA_IHA')
    allergy_medicine = models.CharField(_('Aimoruk (Medicine)'), max_length=255, blank=True, null=True, help_text=_("Specify medicine if allergy exists"))
    
    prescription_text = models.TextField(_('R/ (Prescription Details)'), help_text=_("Enter the complete prescription details here"))
    
    doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='prescriptions', verbose_name=_('Doutor/a'))
    
    SOURCE_CHOICES = [
        ('OPD', 'OPD'),
        ('IGD', 'IGD'),
    ]
    source = models.CharField(_('Source'), max_length=3, choices=SOURCE_CHOICES, default='OPD')

    DISPENSING_STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('DISPENSING', _('Dispensing')),
        ('DISPENSED', _('Dispensed')),
        ('COLLECTED', _('Collected by Patient')),
    ]
    dispensing_status = models.CharField(_('Dispensing Status'), max_length=20, choices=DISPENSING_STATUS_CHOICES, default='PENDING')
    dispensed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='dispensed_prescriptions', verbose_name=_('Dispensed By'))
    dispensed_at = models.DateTimeField(_('Dispensed At'), blank=True, null=True)
    dispensing_notes = models.TextField(_('Dispensing Notes'), blank=True, null=True)

    class Meta:
        verbose_name = _('Prescription')
        verbose_name_plural = _('Prescriptions')
        ordering = ['-date_created']

    def __str__(self):
        return f"Prescription {self.uuid} - {self.visit.patient.full_name}"


class DispensedItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='dispensed_items', verbose_name=_('Prescription'))
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT, related_name='dispensed_items', verbose_name=_('Medicine'))
    quantity = models.PositiveIntegerField(_('Quantity'))
    dosage_instructions = models.CharField(_('Dosage Instructions'), max_length=255, blank=True, null=True, help_text=_("e.g. 3x1 after meal"))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Dispensed Item')
        verbose_name_plural = _('Dispensed Items')
        unique_together = ['prescription', 'medicine']

    def __str__(self):
        return f"{self.medicine.name} x{self.quantity} - {self.prescription}"
