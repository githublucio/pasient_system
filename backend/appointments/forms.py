from django import forms
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import Appointment


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            'patient', 'department', 'doctor',
            'appointment_date', 'appointment_time',
            'reason', 'notes',
        ]
        widgets = {
            'patient': forms.Select(attrs={
                'class': 'form-select select2-ajax-patients',
                'data-ajax-url': reverse_lazy('api_patient_search')
            }),
            'department': forms.Select(attrs={'class': 'form-select select2-basic'}),
            'doctor': forms.Select(attrs={'class': 'form-select select2-basic'}),
            'appointment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'appointment_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

    def clean_appointment_date(self):
        date = self.cleaned_data.get('appointment_date')
        if date and date < timezone.localdate():
            raise forms.ValidationError(_("Appointment date cannot be in the past."))
        return date
