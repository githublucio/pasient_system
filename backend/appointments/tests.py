from django.test import TestCase, Client
from django.contrib.auth.models import User, Permission
from django.utils import timezone
from .models import Appointment
from .forms import AppointmentForm
from patients.models import Patient
from datetime import date, time, timedelta


class AppointmentModelTest(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            patient_id='MD20260010', full_name='Apt Test',
            date_of_birth=date(1990, 1, 1), gender='M'
        )

    def test_appointment_creation(self):
        apt = Appointment.objects.create(
            patient=self.patient,
            appointment_date=date.today() + timedelta(days=1),
            appointment_time=time(10, 0),
            status='SCHEDULED'
        )
        self.assertEqual(apt.status, 'SCHEDULED')
        self.assertEqual(apt.patient, self.patient)

    def test_appointment_cancel(self):
        apt = Appointment.objects.create(
            patient=self.patient,
            appointment_date=date.today() + timedelta(days=1),
            appointment_time=time(10, 0),
        )
        apt.status = 'CANCELLED'
        apt.cancelled_reason = 'Patient request'
        apt.save()
        apt.refresh_from_db()
        self.assertEqual(apt.status, 'CANCELLED')


class AppointmentFormTest(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            patient_id='MD20260011', full_name='Form Test',
            date_of_birth=date(1990, 1, 1), gender='M'
        )

    def test_past_date_rejected(self):
        form = AppointmentForm(data={
            'patient': self.patient.pk,
            'appointment_date': (date.today() - timedelta(days=1)).isoformat(),
            'appointment_time': '10:00',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('appointment_date', form.errors)

    def test_future_date_accepted(self):
        form = AppointmentForm(data={
            'patient': self.patient.pk,
            'appointment_date': (date.today() + timedelta(days=1)).isoformat(),
            'appointment_time': '10:00',
        })
        self.assertTrue(form.is_valid())


class AppointmentAuthTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_calendar_requires_login(self):
        response = self.client.get('/appointments/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_create_requires_login(self):
        response = self.client.get('/appointments/create/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
