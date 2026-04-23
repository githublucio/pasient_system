from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Medicine, StockEntry, Prescription, DispensedItem
from medical_records.models import Visit, Room
from patients.models import Patient
from datetime import date
from django.utils import timezone


class MedicineModelTest(TestCase):
    def test_medicine_creation(self):
        med = Medicine.objects.create(name='Paracetamol', strength='500mg', form='TABLET', unit='TABLET', stock=100)
        self.assertEqual(str(med), f"{med.display_name} - Stock: 100")
        self.assertFalse(med.is_low_stock)

    def test_low_stock_alert(self):
        med = Medicine.objects.create(name='Amoxicillin', unit='CAPSULE', stock=5, min_stock=10)
        self.assertTrue(med.is_low_stock)

    def test_stock_not_negative(self):
        med = Medicine.objects.create(name='Test Med', stock=0, min_stock=10)
        self.assertEqual(med.stock, 0)


class StockEntryTest(TestCase):
    def setUp(self):
        self.medicine = Medicine.objects.create(name='Ibuprofen', stock=0, min_stock=10)

    def test_stock_entry_updates_medicine_stock(self):
        """Stock entry should be created and remaining_qty set."""
        entry = StockEntry.objects.create(
            medicine=self.medicine, quantity=50, remaining_qty=50,
            purchase_date=timezone.localdate(),
            created_by=None
        )
        self.assertEqual(entry.remaining_qty, 50)

    def test_expired_stock(self):
        entry = StockEntry.objects.create(
            medicine=self.medicine, quantity=20, remaining_qty=20,
            expiry_date=date(2020, 1, 1), purchase_date=timezone.localdate()
        )
        self.assertTrue(entry.is_expired)


class PharmacyAuthTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_pharmacy_dashboard_requires_login(self):
        response = self.client.get('/pharmacy/dashboard/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_medicine_list_requires_login(self):
        response = self.client.get('/pharmacy/medicines/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
