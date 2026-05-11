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
        - Superadmins, HIV Staff, OPD/IGD Doctors: Full access.
        - Everyone else: Can see the existence of visits for statistical purposes, 
          but HIV visits are filtered out from general views.
        """
        if user.is_superuser:
            return self
        
        is_hiv_staff = False
        is_opd_igd_staff = False
        staff_profile = getattr(user, 'staff_profile', None)
        if staff_profile and staff_profile.department:
            try:
                dept_code = staff_profile.department.code.upper()
                is_hiv_staff = dept_code in ['HIV', 'AIDS']
                is_opd_igd_staff = dept_code in ['DOKTER', 'OPD', 'IGD', 'EMERGENCY']
            except AttributeError:
                pass

        if is_hiv_staff or is_opd_igd_staff:
            return self
        else:
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
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='visits', verbose_name=_('Patient'))
    
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
        - Superadmin, HIV Staff, OPD/IGD Doctors: Always.
        - Others: ONLY if the patient has NO HIV history and it's not an HIV visit.
        """
        if user.is_superuser:
            return True
        
        is_hiv_staff = False
        is_opd_igd_staff = False
        staff_profile = getattr(user, 'staff_profile', None)
        if staff_profile and staff_profile.department:
            try:
                dept_code = staff_profile.department.code.upper()
                is_hiv_staff = dept_code in ['HIV', 'AIDS']
                is_opd_igd_staff = dept_code in ['DOKTER', 'OPD', 'IGD', 'EMERGENCY']
            except AttributeError:
                pass
        
        if is_hiv_staff or is_opd_igd_staff:
            return True
        
        # Non-HIV/OPD staff: strictly blocked from viewing the clinical details of any HIV-specific visit
        if self.current_room and self.current_room.code == 'HIV':
            return False
            
        return True
    
    # Workflow
    current_room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='current_visits', verbose_name=_('Current Room'))
    visit_fee = models.DecimalField(_('Visit Fee (USD)'), max_digits=10, decimal_places=2, default=0.00)

    # Clinical Data (Chief Complaint remains here as core part of visit)
    complaint = models.TextField(_('Chief Complaint'), blank=True, null=True)
    
    # NOTE: Vital signs are now moved to VitalSigns model (1:1 with Visit)
    # NOTE: Diagnoses are now moved to VisitDiagnosis model (M:M with Visit)
    
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

    @property
    def vitals(self):
        try:
            return self.vital_signs_record
        except:
            return None

    @property
    def primary_diagnosis(self):
        vd = self.visit_diagnoses.filter(is_primary=True).first()
        return vd.diagnosis if vd else None

    @property
    def secondary_diagnoses_list(self):
        return [vd.diagnosis for vd in self.visit_diagnoses.filter(is_primary=False)]

    class Meta:
        verbose_name = _("Visit")
        verbose_name_plural = _("Visits")
        indexes = [
            models.Index(fields=['visit_date', 'status'], name='idx_visit_date_status'),
            models.Index(fields=['current_room', 'status'], name='idx_visit_room_status'),
            models.Index(fields=['patient', '-visit_date'], name='idx_visit_patient_date'),
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
        # Auto-tag logic (Updated for VisitDiagnosis)
        if not self.patient.is_hiv_patient or not self.patient.is_tb_patient:
            room_code = self.current_room.code.upper() if self.current_room else ''
            
            # Tag as HIV
            if room_code in ['HIV', 'AIDS']:
                self.patient.is_hiv_patient = True
            
            # Tag as TB
            if room_code == 'TB':
                self.patient.is_tb_patient = True
            
            self.patient.save(update_fields=['is_hiv_patient', 'is_tb_patient'])

    def __str__(self):
        return f"Visit {self.patient.full_name} - {self.visit_date.date()}"


class VisitDiagnosis(models.Model):
    """
    ERD FINAL: Many-to-Many relation for multiple diagnoses per visit.
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='visit_diagnoses')
    diagnosis = models.ForeignKey(Diagnosis, on_delete=models.PROTECT, related_name='visit_records')
    is_primary = models.BooleanField(_('Primary Diagnosis'), default=False)
    notes = models.TextField(_('Specific Diagnosis Notes'), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Visit Diagnosis')
        verbose_name_plural = _('Visit Diagnoses')
        unique_together = ('visit', 'diagnosis')

    def __str__(self):
        return f"{self.visit} - {self.diagnosis} ({'Primary' if self.is_primary else 'Secondary'})"


class VitalSigns(models.Model):
    """
    ERD FINAL: Dedicated model for vital signs (1:1 with Visit).
    """
    VAS_CHOICES = [
        ('0', _('0 (No Pain)')),
        ('1-3', _('1-3 (Mild)')),
        ('4-6', _('4-6 (Moderate)')),
        ('7-9', _('7-9 (Severe)')),
        ('10', _('10 (Worst Pain)')),
    ]

    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='vital_signs_record', verbose_name=_('Visit'), null=True, blank=True)
    
    # Core Vitals
    bp_sys = models.IntegerField(_('BP Systolic'), blank=True, null=True)
    bp_dia = models.IntegerField(_('BP Diastolic'), blank=True, null=True)
    spo2 = models.IntegerField(_('SPO2 (%)'), blank=True, null=True)
    pulse = models.IntegerField(_('Pulse (bpm)'), blank=True, null=True)
    rr = models.IntegerField(_('Respiratory Rate (bpm)'), blank=True, null=True)
    temp = models.DecimalField(_('Temperature (°C)'), max_digits=4, decimal_places=1, blank=True, null=True)
    weight = models.DecimalField(_('Weight (kg)'), max_digits=5, decimal_places=1, blank=True, null=True)
    height_cm = models.DecimalField(_('Height (cm)'), max_digits=5, decimal_places=1, blank=True, null=True)
    muac = models.DecimalField(_('MUAC (cm)'), max_digits=4, decimal_places=1, blank=True, null=True)
    vas_score = models.CharField(_('VAS Pain Score'), max_length=5, choices=VAS_CHOICES, blank=True, null=True)
    
    # MCH / KIA specific
    kia_category = models.CharField(_('MCH Category'), max_length=20, blank=True, null=True)
    
    # Emergency Specifics (Re-checks)
    er_bp_sys = models.IntegerField(_('ER BP Systolic'), blank=True, null=True)
    er_bp_dia = models.IntegerField(_('ER BP Diastolic'), blank=True, null=True)
    er_spo2 = models.IntegerField(_('ER SPO2 (%)'), blank=True, null=True)
    er_pulse = models.IntegerField(_('ER Pulse (bpm)'), blank=True, null=True)
    er_temp = models.DecimalField(_('ER Temperature (°C)'), max_digits=4, decimal_places=1, blank=True, null=True)
    
    notes = models.TextField(_('Vitals Notes'), blank=True, null=True)
    taken_at = models.DateTimeField(_('Time Taken'), auto_now_add=True)

    class Meta:
        verbose_name = _('Vital Signs')
        verbose_name_plural = _('Vital Signs')

    def __str__(self):
        return f"Vitals for {self.visit}"


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
    vas_score = models.CharField(_('VAS Pain Score'), max_length=5, choices=VitalSigns.VAS_CHOICES, blank=True, null=True)
    
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

class HIVAssessment(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='hiv_assessments', verbose_name=_('Patient'))
    visit = models.ForeignKey(Visit, on_delete=models.SET_NULL, null=True, blank=True, related_name='hiv_assessments', verbose_name=_('Visit'))
    
    # Registration Details specific to HIV
    date_registered_at_bpc = models.DateField(_('Date of registration at BPC'), default=timezone.localdate)
    PATIENT_TYPE_CHOICES = [
        ('NEW', _('New patient')),
        ('TRANSFER', _('Transfer in')),
    ]
    patient_type = models.CharField(_('Patient Type'), max_length=10, choices=PATIENT_TYPE_CHOICES, default='NEW')
    previous_registrations = models.CharField(_('Previous registrations (if applicable)'), max_length=255, blank=True, null=True)
    previous_art = models.CharField(_('Previous ART (if applicable)'), max_length=255, blank=True, null=True)
    
    # Diagnosis Details
    first_positive_test_date = models.DateField(_('Date of first positive test'), blank=True, null=True)
    confirmation_test_seen = models.BooleanField(_('Confirmation test seen?'), default=False)
    where_test_done = models.CharField(_('Where test done'), max_length=255, blank=True, null=True)
    
    # Decision made re: prophylaxis
    prophylaxis_inh = models.BooleanField(_('INH'), default=False, help_text=_('All new patients unless active TB'))
    prophylaxis_cotrimoxazole = models.BooleanField(_('Co-trimoxazole'), default=False, help_text=_('adults CD4<350 or TB, children <5'))
    prophylaxis_fluconazole = models.BooleanField(_('Fluconazole'), default=False, help_text=_('crypto meningitis treated or CD4<100 and CrAg+'))
    
    # Further investigation & Plans
    investigation_tb_needed = models.TextField(_('Further investigation for TB needed?'), blank=True, null=True)
    contraception_plans = models.TextField(_('Plans for contraception'), blank=True, null=True)
    
    # ART
    planned_for_art = models.BooleanField(_('Is the patient planned for ART?'), default=False)
    art_regime = models.CharField(_('ART Regime'), max_length=255, blank=True, null=True)
    
    # Next Visit & Others
    next_visit_scheduled = models.DateField(_('Next visit scheduled'), blank=True, null=True)
    other_plans = models.TextField(_('Plans / investigations / others'), blank=True, null=True)
    
    # Admin
    completed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Completed by'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('HIV Assessment')
        verbose_name_plural = _('HIV Assessments')
        ordering = ['-created_at']

    def __str__(self):
        return f"HIV Assessment for {self.patient.full_name} on {self.created_at.date()}"


class TBScreening(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True, related_name='tb_screenings', verbose_name=_('Registered Patient'))
    
    # If not registered yet
    full_name = models.CharField(_('Full Name'), max_length=255, blank=True, null=True)
    phone_number = models.CharField(_('Phone Number'), max_length=20, blank=True, null=True)
    age = models.IntegerField(_('Age'), blank=True, null=True)
    gender = models.CharField(_('Gender'), max_length=10, choices=[('M', _('Male')), ('F', _('Female'))], blank=True, null=True)

    # Location
    municipio = models.ForeignKey('patients.Municipio', on_delete=models.SET_NULL, null=True, blank=True)
    posto = models.ForeignKey('patients.PostoAdministrativo', on_delete=models.SET_NULL, null=True, blank=True)
    suco = models.ForeignKey('patients.Suco', on_delete=models.SET_NULL, null=True, blank=True)
    aldeia = models.ForeignKey('patients.Aldeia', on_delete=models.SET_NULL, null=True, blank=True)
    outreach_location = models.CharField(_('Specific Location/Site'), max_length=255, blank=True, null=True, help_text="e.g. Market, School, Church")

    # Symptoms
    has_cough_2_weeks = models.BooleanField(_('Cough > 2 Weeks'), default=False)
    has_fever = models.BooleanField(_('Fever'), default=False)
    has_night_sweats = models.BooleanField(_('Night Sweats'), default=False)
    has_weight_loss = models.BooleanField(_('Unexplained Weight Loss'), default=False)
    
    # Risk Factors
    has_contact_history = models.BooleanField(_('Contact with TB Patient'), default=False)
    is_hiv_positive = models.BooleanField(_('Known HIV Positive'), default=False)

    # Result
    is_suspect = models.BooleanField(_('Is TB Suspect'), default=False)
    
    REFERRAL_CHOICES = [
        ('NONE', _('No Referral')),
        ('CLINIC', _('Referred to Clinic')),
        ('LAB', _('Referred to Lab (Sputum)')),
    ]
    referral_status = models.CharField(_('Referral Status'), max_length=10, choices=REFERRAL_CHOICES, default='NONE')
    sputum_collected = models.BooleanField(_('Sputum Sample Collected on Site'), default=False)
    
    # Lab Confirmation (Updated later)
    LAB_RESULT_CHOICES = [
        ('PENDING', _('Pending / Waiting for Lab')),
        ('POSITIVE', _('Positive TB')),
        ('NEGATIVE', _('Negative TB')),
        ('INVALID', _('Invalid / Retest Needed')),
    ]
    lab_result = models.CharField(_('Lab Confirmation Result'), max_length=20, choices=LAB_RESULT_CHOICES, default='PENDING')
    lab_test_date = models.DateField(_('Date Lab Result Received'), blank=True, null=True)
    
    notes = models.TextField(_('Notes'), blank=True, null=True)
    
    screened_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='performed_tb_screenings')
    screening_date = models.DateField(_('Screening Date'), default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('TB Screening Outreach')
        verbose_name_plural = _('TB Screening Outreach Logs')
        ordering = ['-screening_date', '-created_at']
        indexes = [
            models.Index(fields=['screening_date', 'is_suspect']),
            models.Index(fields=['suco', 'aldeia']),
        ]

    def __str__(self):
        name = self.patient.full_name if self.patient else self.full_name
        return f"TB Screening: {name} ({self.screening_date})"


class TBCase(models.Model):
    """
    Master record for a TB treatment episode (TB Treatment Card).
    """
    CASE_TYPES = [
        ('PTB_POS', _('PTB+ (Pulmonary TB Sputum Positive)')),
        ('PTB_NEG', _('PTB- (Pulmonary TB Sputum Negative)')),
        ('EPTB', _('EPTB (Extra-Pulmonary TB)')),
    ]
    CATEGORIES = [
        ('CAT_I', _('Category I (New Cases)')),
        ('CAT_II', _('Category II (Previously Treated)')),
        ('CAT_P', _('Pediatric (Children)')),
        ('CAT_MDR', _('MDR-TB')),
    ]
    OUTCOMES = [
        ('PENDING', _('Still on Treatment')),
        ('CURED', _('Cured')),
        ('COMPLETED', _('Treatment Completed')),
        ('DIED', _('Died')),
        ('FAILED', _('Treatment Failed')),
        ('LOST', _('Lost to Follow-up')),
        ('TRANSFERRED', _('Transferred Out')),
    ]

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='tb_cases', verbose_name=_('Patient'))
    tb_registration_number = models.CharField(_('TB Reg Number'), max_length=50, unique=True, help_text=_("National TB Program Number"))
    
    date_started = models.DateField(_('Treatment Start Date'))
    case_type = models.CharField(_('Case Type'), max_length=10, choices=CASE_TYPES)
    category = models.CharField(_('Treatment Category'), max_length=10, choices=CATEGORIES)
    
    # Diagnosis details
    initial_weight = models.DecimalField(_('Weight at Start (kg)'), max_digits=5, decimal_places=2)
    
    # Clinical Classification
    CLASSIFICATION_CHOICES = [
        ('P', _('Pulmonar')),
        ('EP', _('Estra-Pulmuar')),
    ]
    classification = models.CharField(max_length=2, choices=CLASSIFICATION_CHOICES, default='P')
    site_of_eptb = models.CharField(max_length=255, blank=True, null=True)
    
    # Patient Type
    TYPE_CHOICES = [
        ('FOUN', _('Foun (New)')),
        ('RELAPSU', _('Relapsu (Relapse)')),
        ('DEPOIS_LAKON', _('Depois lakon (After loss to follow up)')),
        ('FALHA', _('Falha (Failure)')),
        ('OUTRU', _('Outru (Other)')),
    ]
    patient_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='FOUN')
    
    # Treatment Regimen
    regimen = models.CharField(max_length=255, blank=True, null=True, help_text="e.g., RHZE (150/75/400/275 mg)")
    
    # Co-morbidities
    hiv_status = models.CharField(max_length=50, blank=True, null=True, help_text="Teste HIV / Data / Rezultadu")
    diabetes_status = models.CharField(max_length=50, blank=True, null=True, help_text="Diabetes Status (FBS/RBG)")
    
    # Lab Results
    initial_sputum = models.CharField(max_length=100, blank=True, null=True)
    initial_xray = models.CharField(max_length=100, blank=True, null=True)
    
    # Treatment Progress (Sputum Follow-up)
    sputum_month_2 = models.CharField(_('Sputum Result (Month 2)'), max_length=20, blank=True, null=True)
    sputum_month_5 = models.CharField(_('Sputum Result (Month 5)'), max_length=20, blank=True, null=True)
    sputum_month_6 = models.CharField(_('Sputum Result (Month 6)'), max_length=20, blank=True, null=True)

    # Outcome
    OUTCOME_CHOICES = [
        ('CURA', _('Kura (Cured)')),
        ('KOMPLETU', _('Tratamentu Kompletu')),
        ('FALHA', _('Falha')),
        ('MATE', _('Mate (Died)')),
        ('LAKON', _('Lakon (Lost to follow up)')),
        ('TRANSFER', _('Transfer (Transferred out)')),
    ]
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, blank=True, null=True)
    date_of_outcome = models.DateField(blank=True, null=True)
    
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    # Persistent storage for all extra fields on the physical form
    card_data = models.JSONField(default=dict, blank=True, help_text=_("Stores additional form data (checkboxes, remarks, etc)"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('TB Case / Treatment Card')
        verbose_name_plural = _('TB Cases')
        ordering = ['-date_started']
        indexes = [
            models.Index(fields=['tb_registration_number'], name='idx_tb_reg_num'),
            models.Index(fields=['date_started'], name='idx_tb_date_started'),
            models.Index(fields=['patient', '-date_started'], name='idx_tb_patient_date'),
            models.Index(fields=['is_active'], name='idx_tb_active'),
        ]

    def __str__(self):
        return f"TB-{self.tb_registration_number} - {self.patient.full_name}"


class TBTreatmentLog(models.Model):
    """
    Daily or Weekly log for TB drug collection and monitoring.
    """
    PHASE_CHOICES = [
        ('INTENSIVE', _('Intensive Phase')),
        ('CONTINUATION', _('Continuation Phase')),
    ]
    
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tb_case = models.ForeignKey(TBCase, on_delete=models.CASCADE, related_name='logs', verbose_name=_('TB Case'))
    visit = models.OneToOneField(Visit, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Associated Visit'))
    
    date_recorded = models.DateField(_('Date'), default=timezone.localdate)
    phase = models.CharField(_('Phase'), max_length=15, choices=PHASE_CHOICES)
    weight = models.DecimalField(_('Weight (kg)'), max_digits=5, decimal_places=2, blank=True, null=True)
    
    drugs_given = models.CharField(_('Drugs Given'), max_length=255, help_text=_("e.g. RHZE, RH"))
    days_supply = models.PositiveIntegerField(_('Days of Supply Given'), default=30)
    
    side_effects = models.TextField(_('Side Effects Noted'), blank=True, null=True)
    is_missed_dose = models.BooleanField(_('Missed Doses?'), default=False)
    
    next_appointment = models.DateField(_('Next Drug Collection Date'), blank=True, null=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_('Recorded By'))

    class Meta:
        verbose_name = _('TB Treatment Log')
        verbose_name_plural = _('TB Treatment Logs')
        ordering = ['-date_recorded']

    def __str__(self):
        return f"Log {self.date_recorded} for {self.tb_case}"


class TBDailyDose(models.Model):
    """
    Daily medication adherence tracking for the TB grid calendar (TB FORM 4).
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tb_case = models.ForeignKey(TBCase, on_delete=models.CASCADE, related_name='daily_doses', verbose_name=_('TB Case'))
    date = models.DateField(_('Date'))
    
    DOSE_STATUS = [
        ('DONE', '✔'),
        ('UNOBSERVED', '-'),
        ('MISSED', '0'),
        ('NONE', ''),
    ]
    status = models.CharField(max_length=10, choices=DOSE_STATUS, default='NONE')
    is_observed = models.BooleanField(_('Observed?'), default=True, help_text=_("True = (✔), False = (-)"))
    notes = models.CharField(_('Notes'), max_length=255, blank=True, null=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_('Recorded By'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('TB Daily Dose')
        verbose_name_plural = _('TB Daily Doses')
        unique_together = ('tb_case', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.date} - {self.tb_case} ({'Observed' if self.is_observed else 'Self'})"

