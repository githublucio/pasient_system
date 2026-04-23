from django.test import TestCase, Client
from .models import RadiologyTest, RadiologyRequest
from medical_records.models import Visit, Room
from patients.models import Patient
from django.contrib.auth.models import User
from datetime import date


class RadiologyModelTest(TestCase):
    def test_radiology_test_creation(self):
        test = RadiologyTest.objects.create(name='Chest X-Ray', order=1)
        self.assertEqual(str(test), test.name)


class RadiologyAuthTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_radiology_dashboard_requires_login(self):
        response = self.client.get('/radiology/dashboard/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
