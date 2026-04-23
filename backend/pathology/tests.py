from django.test import TestCase, Client
from .models import PathologyTest, PathologyRequest
from medical_records.models import Visit, Room
from patients.models import Patient
from django.contrib.auth.models import User
from datetime import date


class PathologyModelTest(TestCase):
    def test_pathology_test_creation(self):
        test = PathologyTest.objects.create(name='Blood Chemistry', order=1)
        self.assertEqual(str(test), test.name)


class PathologyAuthTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_pathology_dashboard_requires_login(self):
        response = self.client.get('/pathology/dashboard/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
