from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
import uuid

class Department(models.Model):
    name = models.CharField(_('Department Name'), max_length=100, unique=True)
    code = models.CharField(_('Code'), max_length=10, unique=True, help_text=_("e.g., LAB, PHA, GEN"))
    description = models.TextField(_('Description'), blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')
        ordering = ['name']
        indexes = [
            GinIndex(name='idx_dept_name_trgm', fields=['name'], opclasses=['gin_trgm_ops']),
        ]

    def __str__(self):
        return self.name

class StaffCategory(models.Model):
    """Professional Title (e.g., Dokter Spesialis, Perawat, Pharmacista)"""
    name = models.CharField(_('Category Name'), max_length=100, unique=True)
    description = models.TextField(_('Description'), blank=True, null=True)

    class Meta:
        verbose_name = _('Staff Category')
        verbose_name_plural = _('Staff Categories')
        ordering = ['name']
        indexes = [
            GinIndex(name='idx_staffcat_name_trgm', fields=['name'], opclasses=['gin_trgm_ops']),
        ]

    def __str__(self):
        return self.name

class Position(models.Model):
    """Administrative Role (e.g., Ketua Departemen, Koordinator, Staff Biasa)"""
    name = models.CharField(_('Position Name'), max_length=100, unique=True)
    description = models.TextField(_('Description'), blank=True, null=True)

    class Meta:
        verbose_name = _('Position')
        verbose_name_plural = _('Positions')
        ordering = ['name']

    def __str__(self):
        return self.name

class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    staff_id = models.CharField(_('Staff ID'), max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='staff_members')
    category = models.ForeignKey(StaffCategory, on_delete=models.PROTECT, related_name='staff_members')
    position = models.ForeignKey(Position, on_delete=models.PROTECT, related_name='staff_members')
    
    phone = models.CharField(_('Phone Number'), max_length=20, blank=True, null=True)
    address = models.TextField(_('Address'), blank=True, null=True)
    bio = models.TextField(_('Biography'), blank=True, null=True)
    photo = models.ImageField(upload_to='staff_photos/', blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Staff Profile')
        verbose_name_plural = _('Staff Profiles')
        indexes = [
            GinIndex(name='idx_staff_id_trgm', fields=['staff_id'], opclasses=['gin_trgm_ops']),
            GinIndex(name='idx_staff_phone_trgm', fields=['phone'], opclasses=['gin_trgm_ops']),
        ]
        permissions = [
            ("can_export_staff", "Can export staff data"),
            ("view_menu_staff", "Can see Staff Management menu in sidebar"),
            ("view_menu_master_data", "Can see Master Data menu in sidebar"),
        ]

    @property
    def is_hiv_staff(self):
        """Returns True if the staff belongs to the HIV/AIDS department."""
        return self.department.code.upper() in ['HIV', 'AIDS']

    @property
    def is_tb_staff(self):
        """Returns True if the staff belongs to the TB department."""
        return self.department.code.upper() == 'TB'

    @property
    def home_url(self):
        """Returns the appropriate dashboard URL based on department code."""
        from django.urls import reverse
        code = self.department.code.upper()
        
        # Mapping mapping codes to relevant URLs
        if code in ['LAB', 'LABORATORY']:
            return reverse('lab_dashboard')
        elif code in ['FAR', 'PHA', 'PHARMACY']:
            return reverse('pharmacy_dashboard')
        elif code in ['RAD', 'RADIOLOGY']:
            return reverse('radiology_dashboard')
        elif code in ['IGD', 'EMERGENCY']:
            return reverse('emergency_dashboard')
        elif code in ['TRIAGE']:
            return reverse('triage_dashboard')
        elif code in ['BILL', 'BILLING']:
            return reverse('billing_dashboard')
        elif code in ['KIA', 'HIV', 'TB', 'DENTAL', 'NUTRISI', 'USG']:
            # For specialist rooms, we use doctor_dashboard with a room filter
            return f"{reverse('doctor_dashboard')}?room={code}"
        
        # Default for medical staff (RJ/General)
        if self.category.name.upper() == 'MEDIS':
            return reverse('doctor_dashboard')
            
        # Fallback to main dashboard
        return reverse('main_dashboard')

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.category.name} ({self.department.name})"
