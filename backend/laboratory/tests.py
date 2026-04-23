from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import LabTest, LabRequest
from medical_records.models import Visit, Room
from patients.models import Patient
from datetime import date


class LabTestModelTest(TestCase):
    def test_lab_test_creation(self):
        test = LabTest.objects.create(name='CBC', code='CBC', order=1)
        self.assertEqual(str(test), test.name)


class LabRequestTest(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            patient_id='MD20260030', full_name='Lab Test Patient',
            date_of_birth=date(1990, 1, 1), gender='M'
        )
        self.room = Room.objects.create(name='Lab', code='LAB', order=7)
        self.visit = Visit.objects.create(
            patient=self.patient, queue_number=1, status='IP', current_room=self.room
        )

    def test_lab_request_creation(self):
        user = User.objects.create_user(username='labtech', password='test123')
        lab_test = LabTest.objects.create(name='CBC', code='CBC', order=1)
        req = LabRequest.objects.create(visit=self.visit, requesting_physician=user)
        req.tests.add(lab_test)
        self.assertEqual(req.tests.count(), 1)
        self.assertEqual(req.status, 'PENDING')


class LabAuthTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_lab_dashboard_requires_login(self):
        response = self.client.get('/lab/dashboard/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
