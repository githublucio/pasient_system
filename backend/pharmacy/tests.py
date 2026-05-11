from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Medicine, StockBatch, Prescription, DispensedItem


class MedicineModelTest(TestCase):
    def test_medicine_creation(self):
        med = Medicine.objects.create(name='Paracetamol', strength='500mg', form='TABLET', unit='TABLET')
        self.assertEqual(str(med), f"{med.display_name} - Stock: 0")
        self.assertTrue(med.is_low_stock)

    def test_stock_calculation(self):
        med = Medicine.objects.create(name='Amoxicillin', unit='CAPSULE', min_stock=10)
        StockBatch.objects.create(
            medicine=med, quantity_received=50, quantity_remaining=50,
            purchase_date=timezone.localdate()
        )
        self.assertEqual(med.total_stock, 50)
        self.assertFalse(med.is_low_stock)


class StockBatchTest(TestCase):
    def setUp(self):
        self.medicine = Medicine.objects.create(name='Ibuprofen', min_stock=10)

    def test_stock_batch_creation(self):
        """Stock batch should be created and quantity_remaining set."""
        batch = StockBatch.objects.create(
            medicine=self.medicine, quantity_received=50, quantity_remaining=50,
            purchase_date=timezone.localdate(),
            created_by=None
        )
        self.assertEqual(batch.quantity_remaining, 50)

    def test_expired_stock(self):
        batch = StockBatch.objects.create(
            medicine=self.medicine, quantity_received=20, quantity_remaining=20,
            expiry_date=date(2020, 1, 1), purchase_date=timezone.localdate()
        )
        self.assertTrue(batch.is_expired)


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
