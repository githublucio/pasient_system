import uuid
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from medical_records.models import Visit

class PathologyTest(models.Model):
    name = models.CharField(_('Test Name'), max_length=100)
    order = models.PositiveIntegerField(_('Order'), default=0)

    class Meta:
        verbose_name = _('Pathology Test')
        verbose_name_plural = _('Pathology Tests')
        ordering = ['order', 'name']
        indexes = [
            GinIndex(name='idx_pathtest_name_trgm', fields=['name'], opclasses=['gin_trgm_ops']),
        ]

    def __str__(self):
        return self.name

class PathologyRequest(models.Model):
    BILLING_CHOICES = [
        ('O', _('Outpatient')),
        ('I', _('Inpatient')),
        ('P', _('Private')),
        ('G', _('Government')),
    ]

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='pathology_request', verbose_name=_('Visit'))
    
    date_of_request = models.DateTimeField(_('Date Requested'), auto_now_add=True)
    requesting_physician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='pathology_requests')
    
    fasting = models.BooleanField(_('Fasting (Jejum)'), default=False)
    clinica_history = models.TextField(_('Clinica History'), blank=True, null=True)
    billing_type = models.CharField(_('Billing'), max_length=1, choices=BILLING_CHOICES, default='O')
    
    # Tubes / Specimen Info
    tube_sst = models.CharField(_('SST'), max_length=100, blank=True, null=True)
    tube_edta = models.CharField(_('EDTA'), max_length=100, blank=True, null=True)
    tube_esr = models.CharField(_('ESR'), max_length=100, blank=True, null=True)
    tube_plain = models.CharField(_('Plain'), max_length=100, blank=True, null=True)
    tube_cit = models.CharField(_('CIT'), max_length=100, blank=True, null=True)
    tube_flok = models.CharField(_('FLOK'), max_length=100, blank=True, null=True)
    tube_msu = models.CharField(_('MSU'), max_length=100, blank=True, null=True)
    tube_swabs = models.CharField(_('Swabs'), max_length=100, blank=True, null=True)
    tube_pap = models.CharField(_('PAP'), max_length=100, blank=True, null=True)
    tube_other = models.CharField(_('Other'), max_length=150, blank=True, null=True)
    
    # Main Tests
    tests = models.ManyToManyField(PathologyTest, verbose_name=_('Tests Requested'), blank=True)

    STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('SAMPLE_COLLECTED', _('Sample Collected')),
        ('IN_PROGRESS', _('In Progress')),
        ('COMPLETED', _('Completed')),
    ]
    SOURCE_CHOICES = [
        ('OPD', _('OPD (Outpatient)')),
        ('IGD', _('IGD (Emergency)')),
    ]
    source = models.CharField(_('Source'), max_length=10, choices=SOURCE_CHOICES, default='OPD')

    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='PENDING')
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_pathology_requests', verbose_name=_('Processed By'))

    class Meta:
        verbose_name = _('Pathology Request')
        verbose_name_plural = _('Pathology Requests')
        ordering = ['-date_of_request']

    def __str__(self):
        return f"Pathology Request {self.uuid} - {self.visit.patient.full_name}"

class PathologyResult(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pathology_request = models.OneToOneField(PathologyRequest, on_delete=models.CASCADE, related_name='result', verbose_name=_('Pathology Request'))
    result_text = models.TextField(_('Result Details'), blank=True, null=True)
    attachment = models.FileField(_('Attachment (PDF)'), upload_to='pathology_results/', blank=True, null=True)
    notes = models.TextField(_('Notes'), blank=True, null=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='verified_pathology_results', verbose_name=_('Verified By'))
    completed_at = models.DateTimeField(_('Completed At'), blank=True, null=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Pathology Result')
        verbose_name_plural = _('Pathology Results')

    def __str__(self):
        return f"Result for {self.pathology_request}"


class PathologyResultAttachment(models.Model):
    pathology_result = models.ForeignKey(PathologyResult, on_delete=models.CASCADE, related_name='attachments', verbose_name=_('Pathology Result'))
    file = models.FileField(_('File'), upload_to='pathology_results/')
    description = models.CharField(_('Description'), max_length=255, blank=True, default='')
    uploaded_at = models.DateTimeField(_('Uploaded At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Pathology Result Attachment')
        verbose_name_plural = _('Pathology Result Attachments')
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Attachment for {self.pathology_result}"
