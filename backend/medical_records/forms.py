from django import forms
from .models import Visit
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy

class TriageForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = [
            'complaint', 'triage_level', 'bp_sys', 'bp_dia', 'spo2', 'pulse', 'rr', 
            'temp', 'weight', 'muac', 'current_room'
        ]
        widgets = {
            'complaint': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': _('Reason for visit (e.g. Fever for 3 days, dry cough...)')}),
            'triage_level': forms.HiddenInput(),
            'bp_sys': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 120 (S)')}),
            'bp_dia': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 80 (D)')}),
            'spo2': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 98%')}),
            'pulse': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 80 bpm')}),
            'rr': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 20 bpm')}),
            'temp': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': _('e.g. 36.5 °C')}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': _('e.g. 60 kg')}),
            'muac': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': _('e.g. 25 cm')}),
            'current_room': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Room
        # Only show rooms 3-6 (Doctors) and EMERGENCY for redirection from Triage
        self.fields['current_room'].queryset = Room.objects.filter(code__in=[
            'ROOM_3', 'ROOM_4', 'ROOM_5', 'ROOM_6', 'EMERGENCY',
            'DOKTER', 'KIA', 'HIV', 'TB', 'DENTAL', 'NUTRISI', 'IGD',
        ])
        self.fields['current_room'].label = _("Next Room (Doctor)")
        self.fields['current_room'].required = True



    def clean_bp_sys(self):
        val = self.cleaned_data.get('bp_sys')
        triage_level = self.cleaned_data.get('triage_level')
        if triage_level == 'BLACK' and val == 0:
            return val
        if val is not None and (val < 40 or val > 300):
            raise forms.ValidationError(_("BP Systolic must be between 40 and 300 mmHg."))
        return val

    def clean_bp_dia(self):
        val = self.cleaned_data.get('bp_dia')
        triage_level = self.cleaned_data.get('triage_level')
        if triage_level == 'BLACK' and val == 0:
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
        triage_level = self.cleaned_data.get('triage_level')
        if triage_level == 'BLACK' and val == 0:
            return val
        if val is not None and (val < 20 or val > 300):
            raise forms.ValidationError(_("Pulse must be between 20 and 300 bpm."))
        return val

    def clean_rr(self):
        val = self.cleaned_data.get('rr')
        triage_level = self.cleaned_data.get('triage_level')
        if triage_level == 'BLACK' and val == 0:
            return val
        if val is not None and (val < 4 or val > 60):
            raise forms.ValidationError(_("Respiratory rate must be between 4 and 60 bpm."))
        return val

    def clean_temp(self):
        val = self.cleaned_data.get('temp')
        triage_level = self.cleaned_data.get('triage_level')
        if triage_level == 'BLACK' and val == 0:
            return val
        if val is not None and (val < 25 or val > 45):
            raise forms.ValidationError(_("Temperature must be between 25 and 45 °C."))
        return val

    def clean_weight(self):
        val = self.cleaned_data.get('weight')
        if val is not None and (val < 0.1 or val > 500):
            # For weight, we might still want a minimum for newborns, 
            # but if it's 0 (maybe placeholder), let's allow 0 for BLACK too
            triage_level = self.cleaned_data.get('triage_level')
            if triage_level == 'BLACK' and val == 0:
                return val
            raise forms.ValidationError(_("Weight must be between 0.1 and 500 kg."))
        return val

class ExaminationForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = [
            'complaint', 'diagnosis', 'secondary_diagnoses', 'clinical_notes', 
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['secondary_diagnoses'].label = _('Secondary Diagnoses')
        self.fields['secondary_diagnoses'].help_text = _('Search and select as many as required. The first one will be treated as Primary.')
        self.fields['status'].required = False
        
        # Room referral logic
        from .models import Room
        referral_codes = ['ROOM_7', 'RADIOLOGY', 'PHARMACY', 'LAB', 'PATHOLOGY', 'IGD', 'EMERGENCY', 'TRAB', 'DENTAL', 'NUTRISI', 'KIA', 'USG']
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
            initial_ids = []
            if self.instance.diagnosis_id:
                initial_ids.append(self.instance.diagnosis_id)
            initial_ids.extend(self.instance.secondary_diagnoses.values_list('id', flat=True))
            self.initial['secondary_diagnoses'] = list(dict.fromkeys(initial_ids)) # Unique list

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Unified logic: Pick the first item from secondary_diagnoses to be the 'Primary'
        # Note: M2M data is in self.cleaned_data['secondary_diagnoses']
        diagnoses = self.cleaned_data.get('secondary_diagnoses', [])
        if diagnoses:
            instance.diagnosis = diagnoses[0]
        else:
            instance.diagnosis = None
            
        if commit:
            instance.save()
            self.save_m2m()
        return instance

class EmergencyExaminationForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = [
            'complaint', 'triage_level', 'er_bp_sys', 'er_bp_dia', 'er_spo2', 'er_pulse', 'er_rr', 
            'er_temp', 'er_weight', 'er_muac', 'vas_score', 'diagnosis', 'secondary_diagnoses', 'clinical_notes', 
            'lab_cbc', 'pharmacy_requested', 'refer_to_central',
            'status', 'allergy_noted',
            'follow_up_date', 'follow_up_notes',
        ]
        widgets = {
            'complaint': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': _('Main emergency complaint (e.g. Acute chest pain, Severe bleeding)...')}),
            'triage_level': forms.HiddenInput(),
            'er_bp_sys': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 120 (S)')}),
            'er_bp_dia': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 80 (D)')}),
            'er_spo2': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 98%')}),
            'er_pulse': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 80 bpm')}),
            'er_rr': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('e.g. 20 bpm')}),
            'er_temp': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': _('e.g. 36.5 °C')}),
            'er_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': _('e.g. 60 kg')}),
            'er_muac': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': _('e.g. 25 cm')}),
            'vas_score': forms.HiddenInput(),
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
    
    allergy_noted = forms.CharField(
        label=_("Identify New Allergy"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. Penicillin, Peanuts')})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['secondary_diagnoses'].label = _('Secondary Diagnoses')
        self.fields['secondary_diagnoses'].help_text = _('Search and select as many as required. The first one will be treated as Primary.')
        self.fields['status'].required = False
        
        from .models import Room
        referral_codes = ['ROOM_7', 'RADIOLOGY', 'PHARMACY', 'LAB', 'PATHOLOGY', 'IGD', 'EMERGENCY', 'TRAB', 'KIA', 'HIV', 'TB', 'DENTAL', 'NUTRISI', 'USG']
        self.fields['referral_rooms'] = forms.ModelMultipleChoiceField(
            queryset=Room.objects.filter(code__in=referral_codes).order_by('name'),
            widget=forms.SelectMultiple(attrs={
                'class': 'form-select select2-multiple',
                'data-placeholder': _('Select one or more departments...')
            }),
            required=False,
            label=_('Next Room / Referrals')
        )

        # Custom VAS choices data for rich UI rendering
        self.fields['vas_score'].choices_data = [
            ('0', _('0 (No Pain)'), '<i class="bi bi-emoji-smile"></i>', '#28a745'),
            ('1-3', _('1-3 (Mild)'), '<i class="bi bi-emoji-neutral"></i>', '#8bc34a'),
            ('4-6', _('4-6 (Moderate)'), '<i class="bi bi-emoji-frown"></i>', '#ffc107'),
            ('7-9', _('7-9 (Severe)'), '<i class="bi bi-emoji-tear"></i>', '#fd7e14'),
            ('10', _('10 (Worst Pain)'), '<i class="bi bi-emoji-dizzy"></i>', '#dc3545'),
        ]

        if self.instance.pk:
            initial_ids = []
            if self.instance.diagnosis_id:
                initial_ids.append(self.instance.diagnosis_id)
            initial_ids.extend(self.instance.secondary_diagnoses.values_list('id', flat=True))
            self.initial['secondary_diagnoses'] = list(dict.fromkeys(initial_ids))

    def save(self, commit=True):
        instance = super().save(commit=False)
        diagnoses = self.cleaned_data.get('secondary_diagnoses', [])
        if diagnoses:
            instance.diagnosis = diagnoses[0]
        else:
            instance.diagnosis = None
            
        if commit:
            instance.save()
            self.save_m2m()
        return instance

    def clean_er_bp_sys(self):
        val = self.cleaned_data.get('er_bp_sys')
        triage_level = self.cleaned_data.get('triage_level')
        if triage_level == 'BLACK' and val == 0:
            return val
        if val is not None and (val < 40 or val > 300):
            raise forms.ValidationError(_("BP Systolic must be between 40 and 300 mmHg."))
        return val

    def clean_er_bp_dia(self):
        val = self.cleaned_data.get('er_bp_dia')
        triage_level = self.cleaned_data.get('triage_level')
        if triage_level == 'BLACK' and val == 0:
            return val
        if val is not None and (val < 20 or val > 200):
            raise forms.ValidationError(_("BP Diastolic must be between 20 and 200 mmHg."))
        return val

    def clean_er_spo2(self):
        val = self.cleaned_data.get('er_spo2')
        if val is not None and (val < 0 or val > 100):
            raise forms.ValidationError(_("SPO2 must be between 0 and 100%."))
        return val

    def clean_er_pulse(self):
        val = self.cleaned_data.get('er_pulse')
        triage_level = self.cleaned_data.get('triage_level')
        if triage_level == 'BLACK' and val == 0:
            return val
        if val is not None and (val < 20 or val > 300):
            raise forms.ValidationError(_("Pulse must be between 20 and 300 bpm."))
        return val

    def clean_er_rr(self):
        val = self.cleaned_data.get('er_rr')
        triage_level = self.cleaned_data.get('triage_level')
        if triage_level == 'BLACK' and val == 0:
            return val
        if val is not None and (val < 4 or val > 60):
            raise forms.ValidationError(_("Respiratory rate must be between 4 and 60 bpm."))
        return val

    def clean_er_temp(self):
        val = self.cleaned_data.get('er_temp')
        triage_level = self.cleaned_data.get('triage_level')
        if triage_level == 'BLACK' and val == 0:
            return val
        if val is not None and (val < 25 or val > 45):
            raise forms.ValidationError(_("Temperature must be between 25 and 45 °C."))
        return val

    def clean_er_weight(self):
        val = self.cleaned_data.get('er_weight')
        triage_level = self.cleaned_data.get('triage_level')
        if triage_level == 'BLACK' and val == 0:
            return val
        if val is not None and (val < 0.1 or val > 500):
            raise forms.ValidationError(_("Weight must be between 0.1 and 500 kg."))
        return val


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
        self.fields['medicine'].queryset = Medicine.objects.filter(is_active=True, stock__gt=0).order_by('name')


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
