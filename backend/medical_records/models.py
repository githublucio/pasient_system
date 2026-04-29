import uuid
from django.db import models
from django.db.models import Q
from django.contrib.postgres.indexes import GinIndex
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from clinic_core.fields import EncryptedTextField
from patients.models import Patient

class Room(models.Model):
    name = models.CharField(_('Room Name'), max_length=100)
    code = models.CharField(_('Room Code'), max_length=20, unique=True, help_text=_("e.g., ROOM_1, TRIAGE, LAB"))
    description = models.TextField(_('Description'), blank=True, null=True)
    order = models.PositiveIntegerField(_('Order'), default=0)

    class Meta:
        verbose_name = _('Room')
        verbose_name_plural = _('Rooms')
        ordering = ['order', 'name']
        indexes = [
            GinIndex(name='idx_room_name_trgm', fields=['name'], opclasses=['gin_trgm_ops']),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

class DiagnosisCategory(models.Model):
    name = models.CharField(_('Category Name'), max_length=100, unique=True)
    description = models.TextField(_('Description'), blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Diagnosis Category')
        verbose_name_plural = _('Diagnosis Categories')

class Diagnosis(models.Model):
    code = models.CharField(_('Diagnosis Code'), max_length=50, unique=True)
    name = models.CharField(_('Description'), max_length=255)
    category = models.ForeignKey(DiagnosisCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='diagnoses', verbose_name=_('Category'))
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_types', 
                               verbose_name=_('Parent Diagnosis'),
                               help_text=_('Leave blank if this is a Top-level Category (Parent)'))

    def __str__(self):
        if self.parent:
            return f"{self.parent.code} > {self.code} - {self.name}"
        return f"{self.code} - {self.name}"

    def get_related_ids(self):
        """Returns IDs of itself and all its descendants for reporting."""
        ids = [self.id]
        for sub in self.sub_types.all():
            ids.extend(sub.get_related_ids())
        return ids

    class Meta:
        verbose_name = _('Diagnosis')
        verbose_name_plural = _('Diagnoses')
        ordering = ['code']
        indexes = [
            GinIndex(name='idx_diag_name_trgm', fields=['name'], opclasses=['gin_trgm_ops']),
            GinIndex(name='idx_diag_code_trgm', fields=['code'], opclasses=['gin_trgm_ops']),
        ]

class VisitQuerySet(models.QuerySet):
    def visible_to(self, user):
        """
        Visibility logic for visits:
        - Superadmins: Full access.
        - Everyone else: Can see the existence of visits for statistical purposes, 
          but HIV visits are filtered out from general views to prevent room disclosure.
        - Privacy of medical content is handled at the model level (can_view_medical_data).
        """
        if user.is_superuser:
            return self
        
        # Robust check for HIV staff status
        is_hiv = False
        staff_profile = getattr(user, 'staff_profile', None)
        if staff_profile:
            # Check department code directly to avoid property overhead/crashes
            try:
                dept_code = staff_profile.department.code.upper()
                is_hiv = dept_code in ['HIV', 'AIDS']
            except AttributeError:
                pass

        if is_hiv:
            # HIV staff can see everything (sensitive and general)
            return self
        else:
            # General staff see everything EXCEPT visits from HIV patients.
            # EXCEPTION (Option 1 modified): Allow visibility ONLY if it's an ACTIVE or TODAY's emergency visit.
            # Past ER visits of HIV patients are fully hidden.
            from django.utils import timezone
            today = timezone.localdate()
            return self.filter(
                Q(patient__is_hiv_patient=False) |
                Q(
                    current_room__code__in=['IGD', 'EMERGENCY'],
                    status__in=['SCH', 'IP']
                ) |
                Q(
                    current_room__code__in=['IGD', 'EMERGENCY'],
                    visit_date__date=today
                )
            ).distinct()

class VisitManager(models.Manager):
    def get_queryset(self):
        return VisitQuerySet(self.model, using=self._db)

    def visible_to(self, user):
        return self.get_queryset().visible_to(user)

class Visit(models.Model):
    STATUS_CHOICES = [
        ('SCH', _('Scheduled')),
        ('IP', _('In Progress')),
        ('COM', _('Completed')),
        ('CAN', _('Cancelled')),
        ('UNC', _('Uncompleted/Expired')),
    ]

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='visits', verbose_name=_('Patient'))
    
    objects = VisitManager()

    doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='doctor_visits', verbose_name=_('Doctor'))
    visit_date = models.DateTimeField(_('Visit Date'), auto_now_add=True)
    queue_number = models.PositiveIntegerField(_('Queue Number'))

    @property
    def has_hiv_history(self):
        """Check if this patient has ANY recorded visit in the HIV department."""
        return Visit.objects.filter(patient=self.patient, current_room__code='HIV').exists()

    def can_view_medical_data(self, user):
        """
        Determines if the user is allowed to see clinical details (diagnosis, notes, vitals).
        - Superadmin: Always.
        - HIV Staff: Always (if it's their patient or general history).
        - Others: ONLY if the patient has NO HIV history and it's not an HIV visit.
        """
        if user.is_superuser:
            return True
        
        is_hiv_staff = False
        if hasattr(user, 'staff_profile'):
            is_hiv_staff = user.staff_profile.is_hiv_staff
        
        if is_hiv_staff:
            return True
        
        # Non-HIV staff: strictly blocked from viewing the clinical details of any HIV-specific visit
        if self.current_room and self.current_room.code == 'HIV':
            return False
            
        return True
    
    # Workflow
    current_room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='current_visits', verbose_name=_('Current Room'))
    visit_fee = models.DecimalField(_('Visit Fee (USD)'), max_digits=10, decimal_places=2, default=0.00)

    # Clinical Data (Triage)
    complaint = models.TextField(_('Chief Complaint'), blank=True, null=True)
    
    # Vital Signs (Explicit Fields)
    bp_sys = models.IntegerField(_('BP Systolic'), blank=True, null=True)
    bp_dia = models.IntegerField(_('BP Diastolic'), blank=True, null=True)
    spo2 = models.IntegerField(_('SPO2 (%)'), blank=True, null=True)
    pulse = models.IntegerField(_('Pulse (bpm)'), blank=True, null=True)
    rr = models.IntegerField(_('Respiratory Rate (bpm)'), blank=True, null=True)
    temp = models.DecimalField(_('Temperature (°C)'), max_digits=4, decimal_places=1, blank=True, null=True)
    weight = models.DecimalField(_('Weight (kg)'), max_digits=5, decimal_places=1, blank=True, null=True)
    VAS_CHOICES = [
        ('0', _('0 (No Pain)')),
        ('1-3', _('1-3 (Mild)')),
        ('4-6', _('4-6 (Moderate)')),
        ('7-9', _('7-9 (Severe)')),
        ('10', _('10 (Worst Pain)')),
    ]
    muac = models.DecimalField(_('MUAC (cm)'), max_digits=4, decimal_places=1, blank=True, null=True)
    vas_score = models.CharField(_('VAS Pain Score'), max_length=5, choices=VAS_CHOICES, blank=True, null=True)

    vital_signs = models.JSONField(_('Vital Signs (Legacy/Notes)'), default=dict, blank=True, help_text=_("Additional vital signs or notes."))
    
    # Emergency Triage Re-Check (To keep initial triage vitals intact)
    er_bp_sys = models.IntegerField(_('ER BP Systolic'), blank=True, null=True)
    er_bp_dia = models.IntegerField(_('ER BP Diastolic'), blank=True, null=True)
    er_spo2 = models.IntegerField(_('ER SPO2 (%)'), blank=True, null=True)
    er_pulse = models.IntegerField(_('ER Pulse (bpm)'), blank=True, null=True)
    er_rr = models.IntegerField(_('ER Respiratory Rate'), blank=True, null=True)
    er_temp = models.DecimalField(_('ER Temperature (°C)'), max_digits=4, decimal_places=1, blank=True, null=True)
    er_weight = models.DecimalField(_('ER Weight (kg)'), max_digits=5, decimal_places=1, blank=True, null=True)
    er_muac = models.DecimalField(_('ER MUAC (cm)'), max_digits=4, decimal_places=1, blank=True, null=True)
    
    diagnosis = models.ForeignKey(Diagnosis, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Diagnosis'))
    secondary_diagnoses = models.ManyToManyField(Diagnosis, blank=True, related_name='secondary_visits', verbose_name=_('Secondary Diagnoses'))
    clinical_notes = EncryptedTextField(_('Clinical Notes'), blank=True, null=True)
    
    # Quick Requests for Rooms 3-6
    lab_cbc = models.BooleanField(_('Request CBC (Lab)'), default=False)
    pharmacy_requested = models.BooleanField(_('Request Pharmacy'), default=False)
    refer_to_central = models.BooleanField(_('Refer to Central Facility'), default=False)
    
    PATIENT_TYPE_CHOICES = [
        ('FOUN', _('New Patient')),
        ('TUAN', _('Returning Patient')),
    ]
    patient_type = models.CharField(_('Patient Type'), max_length=4, choices=PATIENT_TYPE_CHOICES, default='FOUN')
    
    status = models.CharField(_('Status'), max_length=3, choices=STATUS_CHOICES, default='SCH')

    SOURCE_CHOICES = [
        ('OPD', _('OPD (Outpatient)')),
        ('IGD', _('IGD (Emergency)')),
    ]
    source = models.CharField(_('Source'), max_length=3, choices=SOURCE_CHOICES, default='OPD')

    # Staff tracking
    checked_in_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='checkin_visits', verbose_name=_('Checked In By'))
    triage_nurse = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='triage_visits', verbose_name=_('Triage Nurse'))

    # Emergency & Triage Specifics
    TRIAGE_CHOICES = [
        ('RED', _('RED (Immediate/Critical)')),
        ('YELLOW', _('YELLOW (Urgent/Observation)')),
        ('GREEN', _('GREEN (Stable/Walking)')),
        ('BLACK', _('BLACK (Deceased/Non-viable)')),
    ]
    triage_level = models.CharField(_('Triage Level'), max_length=10, choices=TRIAGE_CHOICES, blank=True, null=True)
    
    ARRIVAL_CHOICES = [
        ('AMBULANCE', _('Ambulance')),
        ('PRIVATE', _('Private Vehicle')),
        ('POLICE', _('Police/Military')),
        ('G_SUCO', _('Government/Suco Vehicle')),
        ('WALK_IN', _('Walk-in')),
    ]
    arrival_mode = models.CharField(_('Arrival Mode'), max_length=20, choices=ARRIVAL_CHOICES, default='WALK_IN')
    brought_by_name = models.CharField(_('Brought By (Person)'), max_length=255, blank=True, null=True)
    companion_name = models.CharField(_('Companion Name'), max_length=255, blank=True, null=True)
    arrival_notes = models.TextField(_('Arrival Details'), blank=True, null=True)

    # Discharge & Referral Outcome
    DISCHARGE_CONDITION = [
        ('IMPROVED', _('Improved')),
        ('STABLE', _('Stable')),
        ('REFERRED', _('Referred')),
        ('APS', _('Against Medical Advice (APS)')),
        ('KABUR', _('Eloped / Ran Away')),
        ('DECEASED', _('Deceased')),
    ]
    discharge_condition = models.CharField(_('Discharge Condition'), max_length=20, choices=DISCHARGE_CONDITION, blank=True, null=True)
    referral_hospital = models.CharField(_('Referred to Hospital'), max_length=255, blank=True, null=True)
    referral_vehicle = models.CharField(_('Referral Vehicle Info'), max_length=255, blank=True, null=True)

    discharge_datetime = models.DateTimeField(_('Discharge Date/Time'), blank=True, null=True)
    discharge_summary = models.TextField(_('Discharge Summary'), blank=True, null=True)

    # Continuation & Follow-up Logic
    continuation_of = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='continuations', verbose_name=_('Continuation Of'))
    follow_up_date = models.DateField(_('Follow-up Date'), blank=True, null=True)
    follow_up_notes = models.CharField(_('Follow-up Notes'), max_length=255, blank=True, null=True)

    @property
    def age_at_visit(self):
        """Calculates patient age at the time of this visit."""
        if not self.patient or not self.patient.date_of_birth:
            return 0
        vdate = self.visit_date.date() if hasattr(self.visit_date, 'date') else self.visit_date
        dob = self.patient.date_of_birth
        age = vdate.year - dob.year - ((vdate.month, vdate.day) < (dob.month, dob.day))
        return max(0, age)

    class Meta:
        verbose_name = _("Visit")
        verbose_name_plural = _("Visits")
        indexes = [
            models.Index(fields=['visit_date', 'status'], name='idx_visit_date_status'),
            models.Index(fields=['current_room', 'status'], name='idx_visit_room_status'),
            models.Index(fields=['patient', '-visit_date'], name='idx_visit_patient_date'),
            models.Index(fields=['diagnosis'], name='idx_visit_diagnosis'),
            models.Index(fields=['patient'], name='idx_visit_patient'),
            GinIndex(name='idx_visit_complaint_trgm', fields=['complaint'], opclasses=['gin_trgm_ops']),
        ]
        permissions = [
            ("can_print_visit", "Can print visit report/summary"),
            ("can_export_visits", "Can export visit data"),
            ("view_menu_medical_records", "Can see Medical Records menu in sidebar"),
            ("view_menu_specialist_kia", "Can see KIA menu in sidebar"),
            ("view_menu_specialist_hiv", "Can see HIV menu in sidebar"),
            ("view_menu_specialist_tb", "Can see TB menu in sidebar"),
            ("view_menu_specialist_dental", "Can see Dental menu in sidebar"),
            ("view_menu_specialist_nutrition", "Can see Nutrition menu in sidebar"),
            ("view_menu_specialist_usg", "Can see USG menu in sidebar"),
            ("view_menu_triage", "Can see Triage menu in sidebar"),
        ]


    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Auto-tag patient as HIV if they enter HIV room or receive HIV diagnosis
        if not self.patient.is_hiv_patient:
            tag_as_hiv = False
            room_code = self.current_room.code.upper() if self.current_room else ''
            if room_code in ['HIV', 'AIDS']:
                tag_as_hiv = True
            elif self.diagnosis:
                diag_code = self.diagnosis.code.upper()
                diag_name = self.diagnosis.name.upper()
                if 'B20' in diag_code or 'B24' in diag_code or 'HIV' in diag_name:
                    tag_as_hiv = True
            
            if tag_as_hiv:
                self.patient.is_hiv_patient = True
                self.patient.save(update_fields=['is_hiv_patient'])

        # Auto-tag patient as TB if they enter TB room or receive TB diagnosis
        if not self.patient.is_tb_patient:
            tag_as_tb = False
            room_code = self.current_room.code.upper() if self.current_room else ''
            if room_code == 'TB':
                tag_as_tb = True
            elif self.diagnosis:
                diag_code = self.diagnosis.code.upper()
                if 'A15' <= diag_code <= 'A19':
                    tag_as_tb = True
            
            if tag_as_tb:
                self.patient.is_tb_patient = True
                self.patient.save(update_fields=['is_tb_patient'])

    def __str__(self):
        return f"Visit {self.patient.full_name} - {self.visit_date.date()}"


class VisitLog(models.Model):
    ACTION_CHOICES = [
        ('CHECK_IN', _('Check-In')),
        ('TRIAGE', _('Triage')),
        ('EXAMINATION', _('Doctor Examination')),
        ('LAB_REQUEST', _('Lab Request Created')),
        ('LAB_RESULT', _('Lab Result Entered')),
        ('RAD_REQUEST', _('Radiology Request Created')),
        ('RAD_RESULT', _('Radiology Result Entered')),
        ('PATHO_REQUEST', _('Pathology Request Created')),
        ('PATHO_RESULT', _('Pathology Result Entered')),
        ('PRESCRIPTION', _('Prescription Created')),
        ('DISPENSED', _('Medicine Dispensed')),
        ('REFERRED', _('Referred to National')),
        ('COMPLETED', _('Visit Completed')),
        ('STATUS_CHANGE', _('Status Changed')),
    ]

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='logs', verbose_name=_('Visit'))
    action = models.CharField(_('Action'), max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_('Performed By'))
    timestamp = models.DateTimeField(_('Timestamp'), auto_now_add=True)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Room'))
    notes = models.TextField(_('Notes'), blank=True, default='')

    class Meta:
        verbose_name = _('Visit Log')
        verbose_name_plural = _('Visit Logs')
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['visit', 'timestamp'], name='idx_visitlog_visit_ts'),
        ]

    def __str__(self):
        return f"{self.get_action_display()} by {self.performed_by} at {self.timestamp}"


class EmergencyObservation(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='observations', verbose_name=_('Visit'))
    check_time = models.DateTimeField(_('Observation Time'), default=timezone.now)
    
    # Periodic Vitals
    bp_sys = models.IntegerField(_('BP Systolic'), blank=True, null=True)
    bp_dia = models.IntegerField(_('BP Diastolic'), blank=True, null=True)
    spo2 = models.IntegerField(_('SPO2 (%)'), blank=True, null=True)
    pulse = models.IntegerField(_('Pulse (bpm)'), blank=True, null=True)
    rr = models.IntegerField(_('Respiratory Rate (bpm)'), blank=True, null=True)
    temp = models.DecimalField(_('Temperature (°C)'), max_digits=4, decimal_places=1, blank=True, null=True)
    vas_score = models.CharField(_('VAS Pain Score'), max_length=5, choices=Visit.VAS_CHOICES, blank=True, null=True)
    
    clinical_notes = models.TextField(_('Observation Progress Notes'), blank=True, null=True)
    checked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Monitored By'))

    class Meta:
        verbose_name = _('Emergency Observation')
        verbose_name_plural = _('Emergency Observations')
        ordering = ['-check_time']


class EmergencyMedication(models.Model):
    ADMIN_TYPE_CHOICES = [
        ('ORAL', _('Oral')),
        ('INJECTION', _('Injection')),
        ('OXYGEN', _('Oxygen')),
        ('IV_FLUIDS', _('IV Fluids')),
        ('TOPICAL', _('Topical')),
    ]

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='emergency_medications', verbose_name=_('Visit'))
    
    medicine = models.ForeignKey('pharmacy.Medicine', on_delete=models.PROTECT, related_name='emergency_administrations', verbose_name=_('Medicine'))
    
    quantity = models.PositiveIntegerField(_('Quantity Given'))
    admin_type = models.CharField(_('Administration Type'), max_length=20, choices=ADMIN_TYPE_CHOICES, default='ORAL')
    dosage_instruction = models.CharField(_('Dose & Instruction'), max_length=255, help_text=_("e.g. 500mg, 1 ampoule, 2L/min"))
    
    ordered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='emergency_prescriptions', verbose_name=_('Ordered By (Doctor)'))
    given_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Administered By (Nurse)'))
    given_at = models.DateTimeField(_('Time Administered'), auto_now_add=True)

    class Meta:
        verbose_name = _('Emergency Medication')
        verbose_name_plural = _('Emergency Medications')
        ordering = ['-given_at']
