from django import forms
from .models import Patient, Municipio, PostoAdministrativo, Suco, Aldeia, PatientID
from django.utils.translation import gettext_lazy as _


class PatientRegistrationForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'patient_id', 'patient_category', 'nationality', 'full_name', 'date_of_birth', 'gender',
            'father_name', 'mother_name',
            'municipio', 'posto_administrativo', 'suco', 'aldeia',
            'address',
            'phone_number', 
            'emergency_contact_name', 'emergency_contact_relation', 
            'emergency_contact_phone', 'emergency_contact_address',
            'registration_fee', 'is_pregnant', 'is_lactating'
        ]
        widgets = {
            'patient_id': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'style': 'background-color: #e9ecef; font-weight: bold;'}),
            'patient_category': forms.Select(attrs={'class': 'form-select', 'id': 'id_patient_category'}),
            'nationality': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_nationality', 'placeholder': _('Enter Country of Origin')}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'id_dob'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_full_name', 'placeholder': _('Enter full name')}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'municipio': forms.Select(attrs={'class': 'form-select', 'id': 'id_municipio'}),
            'posto_administrativo': forms.Select(attrs={'class': 'form-select', 'id': 'id_posto', 'disabled': 'disabled'}),
            'suco': forms.Select(attrs={'class': 'form-select', 'id': 'id_suco', 'disabled': 'disabled'}),
            'aldeia': forms.Select(attrs={'class': 'form-select', 'id': 'id_aldeia', 'disabled': 'disabled'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Additional address / house number (optional)')}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Name')}),
            'emergency_contact_relation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Relationship (e.g. Spouse, Sibling)')}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Phone number')}),
            'emergency_contact_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Address')}),
            'registration_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'father_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_father_name'}),
            'mother_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_mother_name'}),
            'is_pregnant': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_lactating': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    id_type = forms.ChoiceField(
        choices=[('', '--- ' + str(_('Select ID Type')) + ' ---')] + PatientID.ID_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_type'})
    )
    id_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_id_number', 'placeholder': _('Passport / Eleitoral / BI Number')})
    )
    
    def __init__(self, *args, **kwargs):
        is_hiv = kwargs.pop('is_hiv', False)
        super().__init__(*args, **kwargs)
        
        if is_hiv:
            self.fields['registration_fee'].initial = 0.00
            self.fields['registration_fee'].widget = forms.HiddenInput()
            self.fields['registration_fee'].required = False

        self.fields['patient_id'].required = False
        
        # Auto-generate next ID if not provided (for new registration)
        if not self.initial.get('patient_id') and not self.instance.pk:
            self.initial['patient_id'] = Patient.generate_next_id()

        self.fields['municipio'].queryset = Municipio.objects.all()
        self.fields['municipio'].empty_label = _("--- Select Municipality ---")
        
        # Populate cascaded querysets if data is present (for form validation/redisplay)
        if 'municipio' in self.data:
            try:
                municipio_id = int(self.data.get('municipio'))
                self.fields['posto_administrativo'].queryset = PostoAdministrativo.objects.filter(municipio_id=municipio_id).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.municipio:
            self.fields['posto_administrativo'].queryset = self.instance.municipio.postos.all().order_by('name')
        else:
            self.fields['posto_administrativo'].queryset = PostoAdministrativo.objects.none()

        if 'posto_administrativo' in self.data:
            try:
                posto_id = int(self.data.get('posto_administrativo'))
                self.fields['suco'].queryset = Suco.objects.filter(posto_id=posto_id).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.posto_administrativo:
            self.fields['suco'].queryset = self.instance.posto_administrativo.sucos.all().order_by('name')
        else:
            self.fields['suco'].queryset = Suco.objects.none()

        if 'suco' in self.data:
            try:
                suco_id = int(self.data.get('suco'))
                self.fields['aldeia'].queryset = Aldeia.objects.filter(suco_id=suco_id).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.suco:
            self.fields['aldeia'].queryset = self.instance.suco.aldeias.all().order_by('name')
        else:
            self.fields['aldeia'].queryset = Aldeia.objects.none()

        self.fields['posto_administrativo'].empty_label = _("--- Select Administrative Post ---")
        self.fields['suco'].empty_label = _("--- Select Village ---")
        self.fields['aldeia'].empty_label = _("--- Select Hamlet ---")

        # Make geographic fields optional
        for f in ['municipio', 'posto_administrativo', 'suco', 'aldeia', 'address']:
            self.fields[f].required = False
            
        # Populate ID fields for editing
        if self.instance.pk:
            first_id = self.instance.identities.first()
            if first_id:
                self.initial['id_type'] = first_id.id_type
                self.initial['id_number'] = first_id.id_number

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            from django.utils import timezone
            if dob > timezone.localdate():
                raise forms.ValidationError(_("Date of birth cannot be in the future."))
        return dob

    def save(self, commit=True):
        patient = super().save(commit=commit)
        if commit:
            id_type = self.cleaned_data.get('id_type')
            id_number = self.cleaned_data.get('id_number')
            if id_type and id_number:
                # Create or update PatientID
                PatientID.objects.update_or_create(
                    patient=patient,
                    id_type=id_type,
                    defaults={'id_number': id_number}
                )
        return patient
