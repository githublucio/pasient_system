from django import forms
from .models import Visit, VitalSigns, Diagnosis, TBCase
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy

class TriageForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['complaint', 'triage_level', 'current_room', 'doctor']
        widgets = {
            'complaint': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': _('Reason for visit (e.g. Fever for 3 days, dry cough...)')}),
            'triage_level': forms.HiddenInput(),
            'current_room': forms.Select(attrs={'class': 'form-select'}),
            'doctor': forms.Select(attrs={'class': 'form-select select2-basic'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Room
        from django.contrib.auth import get_user_model
        User = get_user_model()

        self.fields['current_room'].queryset = Room.objects.filter(code__in=[
            'ROOM_3', 'ROOM_4', 'ROOM_5', 'ROOM_6', 'EMERGENCY',
            'DOKTER', 'KIA', 'HIV', 'TB', 'DENTAL', 'NUTRISI', 'IGD',
        ])
        self.fields['current_room'].label = _("Next Room / Department")
        self.fields['current_room'].required = True

        from django.db.models import Q
        self.fields['doctor'].queryset = User.objects.filter(
            Q(staff_profile__category__name__icontains='Medis') |
            Q(staff_profile__category__name__icontains='Dokter') |
            Q(staff_profile__category__name__icontains='Doctor')
        ).distinct().order_by('first_name')
        self.fields['doctor'].label = _("Select Doctor (Optional)")
        self.fields['doctor'].empty_label = _("--- Any Available Doctor ---")
        self.fields['doctor'].required = False

class TBCaseForm(forms.ModelForm):
    class Meta:
        model = TBCase
        fields = [
            'patient', 'tb_registration_number', 'category', 'date_started', 
            'initial_weight', 'classification', 'site_of_eptb', 'patient_type',
            'regimen', 'hiv_status', 'diabetes_status', 'initial_sputum', 'initial_xray'
        ]
        widgets = {
            'date_started': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class VitalSignsForm(forms.ModelForm):
    class Meta:
        model = VitalSigns
        fields = [
            'bp_sys', 'bp_dia', 'spo2', 'pulse', 'rr', 
            'temp', 'weight', 'muac', 'vas_score'
        ]
        widgets = {
            'bp_sys': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 120 (S)')}),
            'bp_dia': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 80 (D)')}),
            'spo2': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 98%')}),
            'pulse': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 80 bpm')}),
            'rr': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 20 bpm')}),
            'temp': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': _('e.g. 36.5 °C')}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': _('e.g. 60 kg')}),
            'muac': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': _('e.g. 25 cm')}),
            'vas_score': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.triage_level = kwargs.pop('triage_level', None)
        super().__init__(*args, **kwargs)

    def clean_bp_sys(self):
        val = self.cleaned_data.get('bp_sys')
        if self.triage_level == 'BLACK' and val == 0:
            return val
        if val is not None and (val < 40 or val > 300):
            raise forms.ValidationError(_("BP Systolic must be between 40 and 300 mmHg."))
        return val

    def clean_bp_dia(self):
        val = self.cleaned_data.get('bp_dia')
        if self.triage_level == 'BLACK' and val == 0:
            return val
        if val is not None and (val < 20 or val > 200):
            raise forms.ValidationError(_("BP Diastolic must be between 20 and 200 mmHg."))
        return val

    def clean_spo2(self):
        val = self.cleaned_data.get('spo2')
        if val is not None and (val < 0 or val > 100):
            raise forms.ValidationError(_("SPO2 must be between 0 and 100%."))
        return val

    def clean_pulse(self):
        val = self.cleaned_data.get('pulse')
        if self.triage_level == 'BLACK' and val == 0:
            return val
        if val is not None and (val < 20 or val > 300):
            raise forms.ValidationError(_("Pulse must be between 20 and 300 bpm."))
        return val

    def clean_rr(self):
        val = self.cleaned_data.get('rr')
        if self.triage_level == 'BLACK' and val == 0:
            return val
        if val is not None and (val < 4 or val > 60):
            raise forms.ValidationError(_("Respiratory rate must be between 4 and 60 bpm."))
        return val

    def clean_temp(self):
        val = self.cleaned_data.get('temp')
        if self.triage_level == 'BLACK' and val == 0:
            return val
        if val is not None and (val < 25 or val > 45):
            raise forms.ValidationError(_("Temperature must be between 25 and 45 °C."))
        return val

    def clean_weight(self):
        val = self.cleaned_data.get('weight')
        if val is not None and (val < 0.1 or val > 500):
            if self.triage_level == 'BLACK' and val == 0:
                return val
            raise forms.ValidationError(_("Weight must be between 0.1 and 500 kg."))
        return val


class ExaminationForm(forms.ModelForm):
    diagnosis = forms.ModelChoiceField(
        queryset=Diagnosis.objects.all(),
        widget=forms.HiddenInput(),
        required=False
    )
    secondary_diagnoses = forms.ModelMultipleChoiceField(
        queryset=Diagnosis.objects.all(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select select2-diagnosis', 
            'data-ajax-url': reverse_lazy('search_diagnosis_ajax'),
            'data-placeholder': _('Search and select one or more diagnoses...')
        }),
        required=False,
        label=_('Diagnoses')
    )

    class Meta:
        model = Visit
        fields = [
            'complaint', 'clinical_notes', 
            'lab_cbc', 'pharmacy_requested', 'refer_to_central',
            'status', 'follow_up_date', 'follow_up_notes'
        ]
        widgets = {
            'complaint': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': _('Reason for consultation (e.g. Persistent cough, chest pain)...')}),
            'diagnosis': forms.HiddenInput(),
            'secondary_diagnoses': forms.SelectMultiple(attrs={
                'class': 'form-select select2-diagnosis', 
                'data-ajax-url': reverse_lazy('search_diagnosis_ajax'),
                'data-placeholder': _('Search and select one or more diagnoses...')
            }),
            'clinical_notes': forms.Textarea(attrs={'rows': 5, 'class': 'form-control', 'placeholder': _('S: Subjective findings\nO: Objective findings (Physical exam)\nA: Assessment (Clinical impression)\nP: Plan (Treatment, medicine, next steps)...')}),
            'lab_cbc': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pharmacy_requested': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'refer_to_central': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'follow_up_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'follow_up_notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. Check lab results')}),
        }

    is_pregnant = forms.BooleanField(required=False, label=_('Is Pregnant'), widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    is_lactating = forms.BooleanField(required=False, label=_('Is Lactating'), widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.patient:
            self.fields['is_pregnant'].initial = self.instance.patient.is_pregnant
            self.fields['is_lactating'].initial = self.instance.patient.is_lactating
        
        self.fields['secondary_diagnoses'].label = _('Secondary Diagnoses')
        self.fields['secondary_diagnoses'].help_text = _('Search and select as many as required. The first one will be treated as Primary.')
        self.fields['status'].required = False
        
        # Room referral logic
        from .models import Room
        referral_codes = ['ROOM_7', 'RADIOLOGY', 'ROOM_8', 'LAB', 'PATHOLOGY', 'IGD', 'EMERGENCY', 'TRAB', 'DENTAL', 'NUTRISI', 'KIA', 'USG', 'HIV', 'TB']
        self.fields['referral_rooms'] = forms.ModelMultipleChoiceField(
            queryset=Room.objects.filter(code__in=referral_codes).order_by('name'),
            widget=forms.SelectMultiple(attrs={
                'class': 'form-select select2-multiple',
                'data-placeholder': _('Select one or more departments...')
            }),
            required=False,
            label=_('Next Room / Referrals')
        )

        # If editing existing visit, combine primary and secondary into the placeholder field
        if self.instance.pk:
            # New logic: Use VisitDiagnosis model
            self.initial['secondary_diagnoses'] = list(
                self.instance.visit_diagnoses.order_by('-is_primary', 'uuid').values_list('diagnosis_id', flat=True)
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if commit:
            instance.save()
            self.save_m2m()

            # Handle VisitDiagnosis (New Model)
            from .models import VisitDiagnosis
            diagnoses = self.cleaned_data.get('secondary_diagnoses', [])
            
            # Update diagnoses: First one is primary
            instance.visit_diagnoses.all().delete()
            for i, diagnosis in enumerate(diagnoses):
                VisitDiagnosis.objects.create(
                    visit=instance,
                    diagnosis=diagnosis,
                    is_primary=(i == 0)
                )

            # Update patient KIA status
            patient = instance.patient
            if patient:
                patient.is_pregnant = self.cleaned_data.get('is_pregnant', False)
                patient.is_lactating = self.cleaned_data.get('is_lactating', False)
                patient.save(update_fields=['is_pregnant', 'is_lactating'])

        return instance

class EmergencyExaminationForm(forms.ModelForm):
    diagnosis = forms.ModelChoiceField(
        queryset=Diagnosis.objects.all(),
        widget=forms.HiddenInput(),
        required=False
    )
    secondary_diagnoses = forms.ModelMultipleChoiceField(
        queryset=Diagnosis.objects.all(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select select2-diagnosis', 
            'data-ajax-url': reverse_lazy('search_diagnosis_ajax'),
            'data-placeholder': _('Search and select one or more diagnoses...')
        }),
        required=False,
        label=_('Diagnoses')
    )

    class Meta:
        model = Visit
        fields = [
            'complaint', 'triage_level', 'clinical_notes', 
            'lab_cbc', 'pharmacy_requested', 'refer_to_central',
            'status', 'allergy_noted',
            'follow_up_date', 'follow_up_notes',
        ]
        widgets = {
            'complaint': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': _('Main emergency complaint (e.g. Acute chest pain, Severe bleeding)...')}),
            'triage_level': forms.HiddenInput(),
            'diagnosis': forms.HiddenInput(),
            'secondary_diagnoses': forms.SelectMultiple(attrs={
                'class': 'form-select select2-diagnosis', 
                'data-ajax-url': reverse_lazy('search_diagnosis_ajax'),
                'data-placeholder': _('Search and select one or more diagnoses...')
            }),
            'clinical_notes': forms.Textarea(attrs={'rows': 5, 'class': 'form-control', 'placeholder': _('S: Emergency history\nO: Immediate findings\nA: Trauma/Emergency status\nP: Immediate treatment & monitoring plan...')}),
            'lab_cbc': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pharmacy_requested': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'refer_to_central': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'follow_up_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'follow_up_notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': _('Instructions for follow-up visit...')}),
        }
    
    is_pregnant = forms.BooleanField(required=False, label=_('Is Pregnant'), widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    is_lactating = forms.BooleanField(required=False, label=_('Is Lactating'), widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    allergy_noted = forms.CharField(
        label=_("Identify New Allergy"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. Penicillin, Peanuts')})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.patient:
            self.fields['is_pregnant'].initial = self.instance.patient.is_pregnant
            self.fields['is_lactating'].initial = self.instance.patient.is_lactating

        self.fields['secondary_diagnoses'].label = _('Secondary Diagnoses')
        self.fields['secondary_diagnoses'].help_text = _('Search and select as many as required. The first one will be treated as Primary.')
        self.fields['status'].required = False
        
        from .models import Room
        referral_codes = ['ROOM_7', 'RADIOLOGY', 'ROOM_8', 'LAB', 'PATHOLOGY', 'IGD', 'EMERGENCY', 'TRAB', 'KIA', 'HIV', 'TB', 'DENTAL', 'NUTRISI', 'USG']
        self.fields['referral_rooms'] = forms.ModelMultipleChoiceField(
            queryset=Room.objects.filter(code__in=referral_codes).order_by('name'),
            widget=forms.SelectMultiple(attrs={
                'class': 'form-select select2-multiple',
                'data-placeholder': _('Select one or more departments...')
            }),
            required=False,
            label=_('Next Room / Referrals')
        )

        if self.instance.pk:
            # New logic: Use VisitDiagnosis model
            self.initial['secondary_diagnoses'] = list(
                self.instance.visit_diagnoses.order_by('-is_primary', 'uuid').values_list('diagnosis_id', flat=True)
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if commit:
            instance.save()
            self.save_m2m()

            # Handle VisitDiagnosis (New Model)
            from .models import VisitDiagnosis
            diagnoses = self.cleaned_data.get('secondary_diagnoses', [])
            
            # Update diagnoses: First one is primary
            instance.visit_diagnoses.all().delete()
            for i, diagnosis in enumerate(diagnoses):
                VisitDiagnosis.objects.create(
                    visit=instance,
                    diagnosis=diagnosis,
                    is_primary=(i == 0)
                )

            # Update patient KIA status
            patient = instance.patient
            if patient:
                patient.is_pregnant = self.cleaned_data.get('is_pregnant', False)
                patient.is_lactating = self.cleaned_data.get('is_lactating', False)
                patient.save(update_fields=['is_pregnant', 'is_lactating'])

        return instance


class EmergencyAdmissionUpdateForm(forms.ModelForm):
    """Update triage and transport info for ER patients."""
    class Meta:
        model = Visit
        fields = [
            'triage_level', 'arrival_mode', 'brought_by_name', 
            'companion_name', 'arrival_notes'
        ]
        widgets = {
            'triage_level': forms.Select(attrs={'class': 'form-select'}),
            'arrival_mode': forms.Select(attrs={'class': 'form-select'}),
            'brought_by_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Who brought the patient?')}),
            'companion_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Companion Name')}),
            'arrival_notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class EmergencyObservationForm(forms.ModelForm):
    """Periodic vital signs for patients in ER observation."""
    class Meta:
        from .models import EmergencyObservation
        model = EmergencyObservation
        fields = [
            'check_time', 'bp_sys', 'bp_dia', 'spo2', 'pulse', 
            'rr', 'temp', 'vas_score', 'checked_by', 'clinical_notes'
        ]
        widgets = {
            'check_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'vas_score': forms.Select(attrs={'class': 'form-select'}),
            'bp_sys': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 120 (S)')}),
            'bp_dia': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 80 (D)')}),
            'spo2': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 98%')}),
            'pulse': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 80 bpm')}),
            'rr': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 20 bpm')}),
            'temp': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': _('e.g. 36.5 °C')}),
            'checked_by': forms.Select(attrs={'class': 'form-select'}),
            'clinical_notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': _('Progress notes...')}),
        }


class EmergencyMedicationForm(forms.ModelForm):
    """Administering medication in ER."""
    class Meta:
        from .models import EmergencyMedication
        model = EmergencyMedication
        fields = ['medicine', 'quantity', 'admin_type', 'dosage_instruction', 'ordered_by', 'given_by']
        widgets = {
            'medicine': forms.Select(attrs={'class': 'form-select select2-meds'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'admin_type': forms.Select(attrs={'class': 'form-select'}),
            'dosage_instruction': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Enter dose and frequency...')}),
            'ordered_by': forms.Select(attrs={'class': 'form-select'}),
            'given_by': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from pharmacy.models import Medicine
        self.fields['medicine'].queryset = Medicine.objects.filter(
            is_active=True
        ).order_by('name')


class EmergencyDischargeForm(forms.ModelForm):
    """Finalizing an ER visit."""
    class Meta:
        model = Visit
        fields = [
            'discharge_condition', 'referral_hospital', 
            'referral_vehicle', 'discharge_summary',
            'follow_up_date', 'follow_up_notes'
        ]
        widgets = {
            'discharge_condition': forms.Select(attrs={'class': 'form-select'}),
            'referral_hospital': forms.TextInput(attrs={'class': 'form-control'}),
            'referral_vehicle': forms.TextInput(attrs={'class': 'form-control'}),
            'discharge_summary': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'follow_up_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'follow_up_notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. Check lab results')}),
        }

class HIVAssessmentForm(forms.ModelForm):
    class Meta:
        from .models import HIVAssessment
        model = HIVAssessment
        fields = [
            'patient_type', 'date_registered_at_bpc', 'previous_registrations', 'previous_art',
            'first_positive_test_date', 'confirmation_test_seen', 'where_test_done',
            'prophylaxis_inh', 'prophylaxis_cotrimoxazole', 'prophylaxis_fluconazole',
            'investigation_tb_needed', 'contraception_plans',
            'planned_for_art', 'art_regime',
            'next_visit_scheduled', 'other_plans'
        ]
        widgets = {
            'patient_type': forms.Select(attrs={'class': 'form-select'}),
            'date_registered_at_bpc': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'previous_registrations': forms.TextInput(attrs={'class': 'form-control'}),
            'previous_art': forms.TextInput(attrs={'class': 'form-control'}),
            'first_positive_test_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'confirmation_test_seen': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'where_test_done': forms.TextInput(attrs={'class': 'form-control'}),
            'prophylaxis_inh': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'prophylaxis_cotrimoxazole': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'prophylaxis_fluconazole': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'investigation_tb_needed': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'contraception_plans': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'planned_for_art': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'art_regime': forms.TextInput(attrs={'class': 'form-control'}),
            'next_visit_scheduled': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'other_plans': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class TBScreeningForm(forms.ModelForm):
    class Meta:
        from .models import TBScreening
        model = TBScreening
        fields = [
            'patient', 'full_name', 'phone_number', 'age', 'gender',
            'municipio', 'posto', 'suco', 'aldeia', 'outreach_location',
            'has_cough_2_weeks', 'has_fever', 'has_night_sweats', 'has_weight_loss',
            'has_contact_history', 'is_hiv_positive',
            'is_suspect', 'referral_status', 'sputum_collected', 'notes',
            'screening_date', 'lab_result', 'lab_test_date'
        ]
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select select2-patient-ajax'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'municipio': forms.Select(attrs={'class': 'form-select'}),
            'posto': forms.Select(attrs={'class': 'form-select'}),
            'suco': forms.Select(attrs={'class': 'form-select'}),
            'aldeia': forms.Select(attrs={'class': 'form-select'}),
            'outreach_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Market, School'}),
            'has_cough_2_weeks': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_fever': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_night_sweats': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_weight_loss': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_contact_history': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_hiv_positive': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_suspect': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'referral_status': forms.Select(attrs={'class': 'form-select'}),
            'sputum_collected': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'screening_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'lab_result': forms.Select(attrs={'class': 'form-select'}),
            'lab_test_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from patients.models import Patient
        # If we have an instance with a patient, keep that patient in the queryset
        if self.instance and self.instance.pk and self.instance.patient:
            self.fields['patient'].queryset = Patient.objects.filter(id=self.instance.patient.id)
        else:
            self.fields['patient'].queryset = Patient.objects.none()
        
        # Limit geography fields to empty initially to speed up load
        self.fields['posto'].queryset = self.fields['posto'].queryset.none()
        self.fields['suco'].queryset = self.fields['suco'].queryset.none()
        self.fields['aldeia'].queryset = self.fields['aldeia'].queryset.none()
