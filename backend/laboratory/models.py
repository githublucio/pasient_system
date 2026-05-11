import uuid
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from medical_records.models import Visit

class LabTest(models.Model):
    COLUMN_CHOICES = [
        (1, 'Column 1'),
        (2, 'Column 2'),
        (3, 'Column 3'),
    ]

    code = models.CharField(_('Code'), max_length=50, unique=True, blank=True, null=True)
    name = models.CharField(_('Test Name'), max_length=100)
    price = models.DecimalField(_('Price (USD)'), max_digits=10, decimal_places=2, default=0.00)
    normal_range = models.CharField(_('Normal Range'), max_length=100, blank=True, null=True)
    unit = models.CharField(_('Unit'), max_length=50, blank=True, null=True)
    column_index = models.IntegerField(_('Form Column'), choices=COLUMN_CHOICES, default=1)
    order = models.PositiveIntegerField(_('Order'), default=0)

    class Meta:
        verbose_name = _('Lab Test')
        verbose_name_plural = _('Lab Tests')
        ordering = ['column_index', 'order', 'name']
        indexes = [
            GinIndex(name='idx_labtest_name_trgm', fields=['name'], opclasses=['gin_trgm_ops']),
            GinIndex(name='idx_labtest_code_trgm', fields=['code'], opclasses=['gin_trgm_ops']),
        ]

    def __str__(self):
        return self.name

class LabRequest(models.Model):
    URGENCY_CHOICES = [
        ('NORMAL', _('Normal')),
        ('URGENT', _('URGENT')),
    ]
    
    PATIENT_TYPE_CHOICES = [
        ('IN', _('IN-patient')),
        ('OUT', _('OUTpatient')),
    ]

    CATEGORY_CHOICES = [
        ('TB_PT', _('TB pt.')),
        ('TB_SUSP', _('TB susp.')),
        ('ANC', _('ANC')),
        ('STI', _('STI')),
        ('OTHERS', _('Others')),
    ]

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='lab_request', verbose_name=_('Visit'))
    
    date_of_request = models.DateTimeField(_('Date of request'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    lab_no = models.CharField(_('Lab No'), max_length=50, blank=True, null=True, unique=True)
    
    patient_type = models.CharField(_('Patient Type'), max_length=10, choices=PATIENT_TYPE_CHOICES, default='OUT')
    urgency = models.CharField(_('Urgency'), max_length=10, choices=URGENCY_CHOICES, default='NORMAL')
    
    tests = models.ManyToManyField(LabTest, verbose_name=_('Test Requests'), blank=True)
    
    special_category = models.CharField(_('Special Category'), max_length=20, choices=CATEGORY_CHOICES, blank=True, null=True)
    others_note = models.CharField(_('Others Note'), max_length=255, blank=True, null=True)
    
    requesting_physician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='lab_requests', verbose_name=_('Requesting Physician'))

    SOURCE_CHOICES = [
        ('OPD', 'OPD'),
        ('IGD', 'IGD'),
    ]
    source = models.CharField(_('Source'), max_length=3, choices=SOURCE_CHOICES, default='OPD')

    STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('SAMPLE_COLLECTED', _('Sample Collected')),
        ('IN_PROGRESS', _('In Progress')),
        ('COMPLETED', _('Completed')),
        ('CANCELLED', _('Cancelled')),
    ]
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='PENDING')
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_lab_requests', verbose_name=_('Processed By'))
    
    # Cancellation Info
    cancel_reason = models.CharField(_('Cancel Reason'), max_length=255, blank=True, null=True)
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_lab_requests', verbose_name=_('Cancelled By'))

    class Meta:
        verbose_name = _('Lab Request')
        verbose_name_plural = _('Lab Requests')
        ordering = ['-date_of_request']

    def __str__(self):
        return f"Lab Request {self.lab_no or self.uuid} - {self.visit.patient.full_name}"


class LabResult(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lab_request = models.OneToOneField(LabRequest, on_delete=models.CASCADE, related_name='result', verbose_name=_('Lab Request'))
    result_text = models.TextField(_('Result Details'), blank=True, null=True)
    result_data = models.JSONField(_('Result Data'), default=dict, blank=True)
    
    FLAG_CHOICES = [
        ('NORMAL', _('Normal')),
        ('HIGH', _('High')),
        ('LOW', _('Low')),
    ]
    flag = models.CharField(_('Flag'), max_length=10, choices=FLAG_CHOICES, default='NORMAL')
    is_abnormal = models.BooleanField(_('Is Abnormal'), default=False)
    
    attachment = models.FileField(_('Attachment (PDF)'), upload_to='lab_results/', blank=True, null=True)
    notes = models.TextField(_('Notes'), blank=True, null=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='verified_lab_results', verbose_name=_('Verified By'))
    completed_at = models.DateTimeField(_('Completed At'), blank=True, null=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Lab Result')
        verbose_name_plural = _('Lab Results')
        indexes = [
            models.Index(fields=['completed_at'], name='idx_labres_completed'),
        ]

    def __str__(self):
        return f"Result for {self.lab_request}"


class LabResultAttachment(models.Model):
    lab_result = models.ForeignKey(LabResult, on_delete=models.CASCADE, related_name='attachments', verbose_name=_('Lab Result'))
    file = models.FileField(_('File'), upload_to='lab_results/')
    description = models.CharField(_('Description'), max_length=255, blank=True, default='')
    uploaded_at = models.DateTimeField(_('Uploaded At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Lab Result Attachment')
        verbose_name_plural = _('Lab Result Attachments')
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Attachment for {self.lab_result}"
