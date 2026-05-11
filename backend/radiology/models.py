import uuid
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from medical_records.models import Visit

class RadiologyTest(models.Model):
    name = models.CharField(_('Test Name'), max_length=100)
    order = models.PositiveIntegerField(_('Order'), default=0)

    class Meta:
        verbose_name = _('Radiology Test')
        verbose_name_plural = _('Radiology Tests')
        ordering = ['order', 'name']
        indexes = [
            GinIndex(name='idx_radtest_name_trgm', fields=['name'], opclasses=['gin_trgm_ops']),
        ]

    def __str__(self):
        return self.name

class RadiologyRequest(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='radiology_request', verbose_name=_('Visit'))
    
    date_of_request = models.DateTimeField(_('Date of Request'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    radiology_no = models.CharField(_('Radiology No'), max_length=50, blank=True, null=True, unique=True)
    tests = models.ManyToManyField(RadiologyTest, verbose_name=_('Test Requests'), blank=True)
    
    requesting_physician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='radiology_requests', verbose_name=_('Medico'))

    STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('IN_PROGRESS', _('In Progress')),
        ('COMPLETED', _('Completed')),
    ]
    SOURCE_CHOICES = [
        ('OPD', _('OPD (Outpatient)')),
        ('IGD', _('IGD (Emergency)')),
    ]
    source = models.CharField(_('Source'), max_length=10, choices=SOURCE_CHOICES, default='OPD')

    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='PENDING')
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='performed_radiology_requests', verbose_name=_('Performed By'))

    class Meta:
        verbose_name = _('Radiology Request')
        verbose_name_plural = _('Radiology Requests')
        ordering = ['-date_of_request']

    def __str__(self):
        return f"Radiology Request {self.uuid} - {self.visit.patient.full_name}"

class RadiologyResult(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    radiology_request = models.OneToOneField(RadiologyRequest, on_delete=models.CASCADE, related_name='result', verbose_name=_('Radiology Request'))
    findings = models.TextField(_('Findings'), blank=True, null=True)
    impression = models.TextField(_('Impression'), blank=True, null=True)
    attachment = models.FileField(_('Attachment (Image/PDF)'), upload_to='radiology_results/', blank=True, null=True)
    notes = models.TextField(_('Notes'), blank=True, null=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='verified_radiology_results', verbose_name=_('Verified By'))
    completed_at = models.DateTimeField(_('Completed At'), blank=True, null=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Radiology Result')
        verbose_name_plural = _('Radiology Results')

    def __str__(self):
        return f"Result for {self.radiology_request}"


class RadiologyResultAttachment(models.Model):
    radiology_result = models.ForeignKey(RadiologyResult, on_delete=models.CASCADE, related_name='attachments', verbose_name=_('Radiology Result'))
    file = models.FileField(_('File'), upload_to='radiology_results/')
    description = models.CharField(_('Description'), max_length=255, blank=True, default='')
    uploaded_at = models.DateTimeField(_('Uploaded At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Radiology Result Attachment')
        verbose_name_plural = _('Radiology Result Attachments')
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Attachment for {self.radiology_result}"
