import uuid
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.operations import TrigramExtension
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from clinic_core.fields import EncryptedTextField
from dateutil.relativedelta import relativedelta
import hashlib


# ─── Timor-Leste Administrative Geography ──────────────────────────────────────

class Municipio(models.Model):
    name = models.CharField(_('Municipality'), max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = _("Municipality")
        verbose_name_plural = _("Municipalities")

    def __str__(self):
        return self.name


class PostoAdministrativo(models.Model):
    municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT, related_name='postos')
    name = models.CharField(_('Administrative Post'), max_length=100)

    class Meta:
        ordering = ['name']
        unique_together = ('municipio', 'name')
        verbose_name = _("Administrative Post")
        verbose_name_plural = _("Administrative Posts")

    def __str__(self):
        return f"{self.name} ({self.municipio.name})"

    def clean(self):
        if self.pk:
            old_instance = PostoAdministrativo.objects.get(pk=self.pk)
            if old_instance.municipio != self.municipio:
                if self.sucos.exists() or self.patients.exists():
                    raise ValidationError(_("Cannot change Municipio because this Posto is already in use by Sucos or Patients."))


class Suco(models.Model):
    posto = models.ForeignKey(PostoAdministrativo, on_delete=models.PROTECT, related_name='sucos')
    name = models.CharField(_('Village (Suco)'), max_length=100)

    class Meta:
        ordering = ['name']
        unique_together = ('posto', 'name')
        verbose_name = _("Village (Suco)")
        verbose_name_plural = _("Villages (Sucos)")

    def __str__(self):
        return f"{self.name} ({self.posto.name})"

    def clean(self):
        if self.pk:
            old_instance = Suco.objects.get(pk=self.pk)
            if old_instance.posto != self.posto:
                if self.aldeias.exists() or self.patients.exists():
                    raise ValidationError(_("Cannot change Posto because this Suco is already in use by Aldeias or Patients."))


class Aldeia(models.Model):
    suco = models.ForeignKey(Suco, on_delete=models.PROTECT, related_name='aldeias')
    name = models.CharField(_('Hamlet (Aldeia)'), max_length=100)

    class Meta:
        ordering = ['name']
        unique_together = ('suco', 'name')
        verbose_name = _("Hamlet (Aldeia)")
        verbose_name_plural = _("Hamlets (Aldeias)")

    def __str__(self):
        return f"{self.name} ({self.suco.name})"

    def clean(self):
        if self.pk:
            old_instance = Aldeia.objects.get(pk=self.pk)
            if old_instance.suco != self.suco:
                if self.patients.exists():
                    raise ValidationError(_("Cannot change Suco because this Aldeia is already in use by Patients."))


# ─── Patient ───────────────────────────────────────────────────────────────────

class PatientQuerySet(models.QuerySet):
    def visible_to(self, user):
        """
        Visibility logic for patients:
        - Superadmins & HIV Staff: Can see all patients.
        - Others: Can ONLY see non-HIV patients.
          EXCEPTION (Option 1): HIV patients become visible to general staff 
          ONLY IF they have an active or today's emergency (IGD) visit.
        """
        from django.db.models import Q

        if user.is_superuser:
            return self
        
        is_hiv_staff = False
        is_nutrition_staff = False
        staff_profile = getattr(user, 'staff_profile', None)
        if staff_profile and staff_profile.department:
            try:
                dept_code = staff_profile.department.code.upper()
                is_hiv_staff = dept_code in ['HIV', 'AIDS']
                is_nutrition_staff = dept_code == 'NUTRISI'
            except AttributeError:
                pass
        
        # Superadmins, HIV Staff, and Nutrition Staff see their respective patients
        if user.is_superuser:
            return self
            
        today = timezone.localdate()
        child_limit = today - relativedelta(months=59)

        # Base filter: Exclude HIV and Nutrition patients from general view
        # Unless they have an active/today's visit in the current user's permitted areas (like IGD)
        qs = self.all()

        if not is_hiv_staff and not is_nutrition_staff:
            from medical_records.models import Visit
            igd_patient_ids = list(Visit.objects.filter(
                Q(current_room__code__in=['IGD', 'EMERGENCY']) & 
                (Q(visit_date__date=today) | Q(status__in=['SCH', 'IP']))
            ).values_list('patient_id', flat=True))
            
            # General Staff: Hide BOTH HIV and Nutrition categories
            qs = qs.filter(
                # Condition A: Not HIV and Not Nutrition
                (Q(is_hiv_patient=False) & Q(is_pregnant=False) & Q(is_lactating=False) & Q(date_of_birth__lt=child_limit)) |
                # Condition B: Emergency exception (if they are in IGD today, everyone can see them for safety)
                Q(uuid__in=igd_patient_ids)
            )
        elif is_nutrition_staff:
            from medical_records.models import Visit
            igd_patient_ids = list(Visit.objects.filter(
                current_room__code__in=['IGD', 'EMERGENCY'],
                visit_date__date=today
            ).values_list('patient_id', flat=True))
            
            # Nutrition Staff: Can see Nutrition patients + General patients, but NO HIV patients
            qs = qs.filter(
                Q(is_hiv_patient=False) |
                Q(uuid__in=igd_patient_ids)
            )
        elif is_hiv_staff:
            # HIV Staff: Usually see everything (as per current system policy)
            return self

        return qs.distinct()

class PatientManager(models.Manager):
    def get_queryset(self):
        return PatientQuerySet(self.model, using=self._db)
    
    def visible_to(self, user):
        return self.get_queryset().visible_to(user)

class Patient(models.Model):
    GENDER_CHOICES = [
        ('M', _('Male')),
        ('F', _('Female')),
        ('O', _('Other')),
    ]

    CATEGORY_CHOICES = [
        ('RAI_LARAN', _('Local')),
        ('RAI_LIUR', _('International')),
    ]

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient_id = models.CharField(_('Patient ID'), max_length=20, unique=True, db_index=True)
    patient_category = models.CharField(_('Patient Category'), max_length=10, choices=CATEGORY_CHOICES, default='RAI_LARAN')
    full_name = models.CharField(_('Full Name'), max_length=255, db_index=True)
    date_of_birth = models.DateField(_('Date of Birth'))
    gender = models.CharField(_('Gender'), max_length=1, choices=GENDER_CHOICES)

    BLOOD_TYPE_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ]
    blood_type = models.CharField(_('Blood Type'), max_length=3, choices=BLOOD_TYPE_CHOICES, blank=True, null=True)

    # Parent Information (Mainly for Local Patients)
    father_name = models.CharField(_('Father Name'), max_length=255, blank=True, null=True)
    mother_name = models.CharField(_('Mother Name'), max_length=255, blank=True, null=True)

    # International Info
    nationality = models.CharField(_('Nationality'), max_length=100, blank=True, null=True)

    # Geographic address (Timor-Leste administrative structure)
    municipio = models.ForeignKey(
        Municipio, on_delete=models.PROTECT, null=True, blank=True,
        verbose_name=_('Municipio'), related_name='patients'
    )
    posto_administrativo = models.ForeignKey(
        PostoAdministrativo, on_delete=models.PROTECT, null=True, blank=True,
        verbose_name=_('Posto Administrativo'), related_name='patients'
    )
    suco = models.ForeignKey(
        Suco, on_delete=models.PROTECT, null=True, blank=True,
        verbose_name=_('Suco'), related_name='patients'
    )
    aldeia = models.ForeignKey(
        Aldeia, on_delete=models.PROTECT, null=True, blank=True,
        verbose_name=_('Aldeia'), related_name='patients'
    )
    address = EncryptedTextField(_('Additional Address / Notes'), blank=True, default='')

    phone_number = EncryptedTextField(_('Phone Number'), max_length=255, blank=True, null=True)
    emergency_contact_name = models.CharField(_('Emergency Contact Name'), max_length=255, blank=True, null=True)
    emergency_contact_phone = EncryptedTextField(_('Emergency Contact Phone'), max_length=255, blank=True, null=True)

    # Images for Card
    qr_code_image = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    barcode_image = models.ImageField(upload_to='barcodes/', blank=True, null=True)

    registration_fee = models.DecimalField(
        _('Contribution (USD)'),
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    is_hiv_patient = models.BooleanField(_('Is HIV Patient'), default=False, db_index=True)
    is_tb_patient = models.BooleanField(_('Is TB Patient'), default=False, db_index=True)
    is_pregnant = models.BooleanField(_('Is Pregnant'), default=False, db_index=True)
    is_lactating = models.BooleanField(_('Is Lactating'), default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PatientManager()

    @property
    def age(self):
        if not self.date_of_birth:
            return 0
        today = timezone.localdate()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

    @property
    def full_address(self):
        parts = [
            self.aldeia.name if self.aldeia else '',
            self.suco.name if self.suco else '',
            self.posto_administrativo.name if self.posto_administrativo else '',
            self.municipio.name if self.municipio else '',
        ]
        return ', '.join(p for p in parts if p) or self.address

    @staticmethod
    def generate_next_id():
        """
        Calculates the next available Patient ID based on the current year.
        Format: MDYYYYXXXX (e.g., MD20260001)
        """
        from django.db.models import Max
        from django.utils import timezone
        
        year = timezone.localdate().year
        prefix = f"MD{year}"
        last_id_data = Patient.objects.filter(patient_id__startswith=prefix).aggregate(
            max_id=Max('patient_id')
        )
        last_id = last_id_data.get('max_id')
        
        if last_id:
            try:
                # Extract the last 4 digits
                last_num = int(last_id[-4:])
                new_num = last_num + 1
            except (ValueError, TypeError, IndexError):
                new_num = 1
        else:
            new_num = 1
            
        return f"{prefix}{new_num:04d}"

    def save(self, *args, **kwargs):
        """
        Custom save to handle potential ID collisions during concurrent registrations.
        """
        if not self.patient_id:
            self.patient_id = self.generate_next_id()
        
        # If this is a new patient, check if the ID was already taken 
        # (race condition between form load and save)
        if not self._state.adding is False: # If it's a new record
            attempts = 0
            while Patient.objects.filter(patient_id=self.patient_id).exists() and attempts < 10:
                self.patient_id = self.generate_next_id()
                attempts += 1
                
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Patient")
        verbose_name_plural = _("Patients")
        indexes = [
            models.Index(fields=['full_name'], name='idx_patient_fullname'),
            models.Index(fields=['phone_number'], name='idx_patient_phone'),
            models.Index(fields=['-created_at'], name='idx_patient_created'),
            GinIndex(name='idx_patient_name_trgm', fields=['full_name'], opclasses=['gin_trgm_ops']),
            GinIndex(name='idx_patient_phone_trgm', fields=['phone_number'], opclasses=['gin_trgm_ops']),
            GinIndex(name='idx_patient_id_trgm', fields=['patient_id'], opclasses=['gin_trgm_ops']),
        ]
        permissions = [
            ("can_print_card", "Can print patient ID card"),
            ("can_export_patients", "Can export patient data"),
            ("view_menu_patients", "Can see Patients menu in sidebar"),
        ]

    def __str__(self):
        return f"{self.patient_id} - {self.full_name}"


class PatientID(models.Model):
    ID_TYPES = [
        ('ELEITORAL', _('National ID (Eleitoral)')),
        ('BI', _('Identity Card (BI)')),
        ('PASSPORT', _('Passport')),
        ('OTHER', _('Other')),
    ]

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='identities')
    id_type = models.CharField(_('ID Type'), max_length=20, choices=ID_TYPES)
    id_number = EncryptedTextField(_('ID Number'))
    id_search_hash = models.CharField(_('Search Hash'), max_length=64, db_index=True)

    class Meta:
        verbose_name = _("Patient Identification")
        verbose_name_plural = _("Patient Identifications")
        unique_together = ('id_type', 'id_search_hash')

    def save(self, *args, **kwargs):
        # Generate SHA-256 hash of the ID number for exact matching
        if self.id_number:
            # Normalize: strip whitespace and uppercase
            normalized = str(self.id_number).strip().upper()
            self.id_search_hash = hashlib.sha256(normalized.encode()).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_id_type_display()} - {self.patient.full_name}"


class PatientAllergy(models.Model):
    SEVERITY_CHOICES = [
        ('MILD', _('Mild')),
        ('MODERATE', _('Moderate')),
        ('SEVERE', _('Severe')),
    ]

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='allergies')
    allergen = models.CharField(_('Allergen'), max_length=200)
    reaction = models.CharField(_('Reaction'), max_length=255, blank=True, null=True)
    severity = models.CharField(_('Severity'), max_length=10, choices=SEVERITY_CHOICES, default='MILD')
    is_active = models.BooleanField(_('Active'), default=True)
    noted_date = models.DateField(_('Date Noted'), auto_now_add=True)

    class Meta:
        verbose_name = _('Patient Allergy')
        verbose_name_plural = _('Patient Allergies')
        ordering = ['-noted_date']

    def __str__(self):
        return f"{self.patient.full_name} - {self.allergen} ({self.get_severity_display()})"


class DailyQueue(models.Model):
    date = models.DateField(default=timezone.now)
    current_number = models.PositiveIntegerField(default=0)
    department = models.CharField(max_length=50, default='General')

    class Meta:
        verbose_name = _("Daily Queue")
        verbose_name_plural = _("Daily Queues")
        unique_together = ['date', 'department']

    def get_next_number(self):
        from django.db.models import F
        DailyQueue.objects.filter(pk=self.pk).update(current_number=F('current_number') + 1)
        self.refresh_from_db()
        return self.current_number

    def __str__(self):
        return f"Queue for {self.date} - {self.department}"
