import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from patients.models import Patient
from medical_records.models import Room


class AppointmentQuerySet(models.QuerySet):
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

class AppointmentManager(models.Manager):
    def get_queryset(self):
        return AppointmentQuerySet(self.model, using=self._db)
    
    def visible_to(self, user):
        return self.get_queryset().visible_to(user)

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', _('Scheduled')),
        ('CONFIRMED', _('Confirmed')),
        ('CHECKED_IN', _('Checked In')),
        ('COMPLETED', _('Completed')),
        ('CANCELLED', _('Cancelled')),
        ('NO_SHOW', _('No Show')),
    ]

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments', verbose_name=_('Patient'))
    department = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Department/Room'))
    doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='doctor_appointments', verbose_name=_('Doctor'))
    
    appointment_date = models.DateField(_('Appointment Date'))
    appointment_time = models.TimeField(_('Appointment Time'))
    
    reason = models.TextField(_('Reason for Visit'), blank=True, null=True)
    notes = models.TextField(_('Notes'), blank=True, null=True)
    
    status = models.CharField(_('Status'), max_length=12, choices=STATUS_CHOICES, default='SCHEDULED')
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_appointments', verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    cancelled_reason = models.TextField(_('Cancellation Reason'), blank=True, null=True)
    
    @property
    def is_late(self):
        """Checks if the appointment is in the past but not yet checked-in/completed."""
        if self.status in ['SCHEDULED', 'CONFIRMED']:
            now = timezone.localtime()
            apt_datetime = timezone.make_aware(timezone.datetime.combine(self.appointment_date, self.appointment_time))
            return now > apt_datetime
        return False

    objects = AppointmentManager()

    class Meta:
        verbose_name = _('Appointment')
        verbose_name_plural = _('Appointments')
        ordering = ['appointment_date', 'appointment_time']
        permissions = [
            ('view_menu_appointments', 'Can see Appointments menu in sidebar'),
        ]

    def __str__(self):
        return f"{self.patient.full_name} - {self.appointment_date} {self.appointment_time}"
