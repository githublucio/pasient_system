from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Visit, Room, Diagnosis
from .forms import TriageForm, EmergencyExaminationForm
from patients.models import Patient
from datetime import date


class VitalSignValidationTest(TestCase):
    """Test vital sign range validators in forms."""

    def setUp(self):
        self.patient = Patient.objects.create(
            patient_id='MD20260001', full_name='Test Patient',
            date_of_birth=date(1990, 1, 1), gender='M'
        )
        self.room = Room.objects.create(name='Triage', code='TRIAGE', order=1)
        # Create the destination rooms needed by TriageForm queryset
        Room.objects.create(name='Room 3', code='ROOM_3', order=3)
        Room.objects.create(name='Emergency', code='EMERGENCY', order=10)
        self.visit = Visit.objects.create(
            patient=self.patient, queue_number=1, status='SCH', current_room=self.room
        )

    def test_bp_sys_too_high_rejected(self):
        form = TriageForm({'bp_sys': 999, 'current_room': Room.objects.get(code='ROOM_3').pk}, instance=self.visit)
        self.assertFalse(form.is_valid())
        self.assertIn('bp_sys', form.errors)

    def test_bp_sys_valid(self):
        room3 = Room.objects.get(code='ROOM_3')
        form = TriageForm({
            'bp_sys': 120, 'bp_dia': 80, 'spo2': 98, 'pulse': 72,
            'rr': 18, 'temp': 36.5, 'weight': 65,
            'current_room': room3.pk
        }, instance=self.visit)
        self.assertTrue(form.is_valid())

    def test_spo2_over_100_rejected(self):
        form = TriageForm({'spo2': 105, 'current_room': Room.objects.get(code='ROOM_3').pk}, instance=self.visit)
        self.assertFalse(form.is_valid())
        self.assertIn('spo2', form.errors)

    def test_temp_below_range_rejected(self):
        form = TriageForm({'temp': 10.0, 'current_room': Room.objects.get(code='ROOM_3').pk}, instance=self.visit)
        self.assertFalse(form.is_valid())
        self.assertIn('temp', form.errors)

    def test_pulse_negative_rejected(self):
        form = TriageForm({'pulse': -5, 'current_room': Room.objects.get(code='ROOM_3').pk}, instance=self.visit)
        self.assertFalse(form.is_valid())
        self.assertIn('pulse', form.errors)


class VisitModelTest(TestCase):
    """Test Visit model and related logic."""

    def setUp(self):
        self.patient = Patient.objects.create(
            patient_id='MD20260002', full_name='Jane Doe',
            date_of_birth=date(1985, 5, 15), gender='F'
        )
        self.room = Room.objects.create(name='Triage', code='TRIAGE2', order=1)

    def test_visit_creation(self):
        visit = Visit.objects.create(
            patient=self.patient, queue_number=1, status='SCH', current_room=self.room
        )
        self.assertEqual(visit.status, 'SCH')
        self.assertEqual(visit.patient, self.patient)

    def test_visit_secondary_diagnoses_m2m(self):
        d1 = Diagnosis.objects.create(code='A00', name='Cholera')
        d2 = Diagnosis.objects.create(code='A01', name='Typhoid')
        visit = Visit.objects.create(
            patient=self.patient, queue_number=1, status='SCH', current_room=self.room
        )
        visit.secondary_diagnoses.add(d1, d2)
        self.assertEqual(visit.secondary_diagnoses.count(), 2)


class MedicalRecordsAuthTest(TestCase):
    """Test that medical record views require authentication."""

    def setUp(self):
        self.client = Client()
        self.patient = Patient.objects.create(
            patient_id='MD20260003', full_name='Auth Test',
            date_of_birth=date(1990, 1, 1), gender='M'
        )
        self.room = Room.objects.create(name='Test Room', code='TEST_ROOM', order=1)
        self.visit = Visit.objects.create(
            patient=self.patient, queue_number=1, status='SCH', current_room=self.room
        )

    def test_triage_input_requires_login(self):
        response = self.client.get(f'/records/triage/input/{self.visit.uuid}/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_visit_detail_requires_login(self):
        response = self.client.get(f'/records/visit/{self.visit.uuid}/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
