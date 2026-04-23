from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import ServiceCategory, ServicePrice, Invoice, InvoiceItem, Payment
from patients.models import Patient
from datetime import date
from decimal import Decimal


class InvoiceTest(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            patient_id='MD20260020', full_name='Bill Test',
            date_of_birth=date(1990, 1, 1), gender='M'
        )
        self.user = User.objects.create_user(username='cashier', password='test123')
        self.category = ServiceCategory.objects.create(name='Consultation', code='CONS')
        self.service = ServicePrice.objects.create(
            category=self.category, name='General Consultation', price=Decimal('5.00')
        )

    def test_invoice_creation(self):
        invoice = Invoice.objects.create(
            invoice_number='INV-20260001', patient=self.patient, created_by=self.user
        )
        self.assertEqual(invoice.status, 'UNPAID')
        self.assertEqual(invoice.total_amount, Decimal('0.00'))

    def test_invoice_recalculate(self):
        invoice = Invoice.objects.create(
            invoice_number='INV-20260002', patient=self.patient,
            created_by=self.user, discount=Decimal('0.00')
        )
        InvoiceItem.objects.create(
            invoice=invoice, service=self.service, category=self.category,
            description='Consultation', quantity=1, unit_price=Decimal('5.00')
        )
        invoice.recalculate()
        self.assertEqual(invoice.total_amount, Decimal('5.00'))

    def test_payment_updates_status(self):
        invoice = Invoice.objects.create(
            invoice_number='INV-20260003', patient=self.patient,
            created_by=self.user, discount=Decimal('0.00')
        )
        InvoiceItem.objects.create(
            invoice=invoice, service=self.service, category=self.category,
            description='Service', quantity=2, unit_price=Decimal('5.00')
        )
        Payment.objects.create(
            invoice=invoice, amount=Decimal('10.00'),
            payment_method='CASH', received_by=self.user
        )
        invoice.amount_paid = Decimal('10.00')
        invoice.recalculate()
        self.assertEqual(invoice.status, 'PAID')


class BillingAuthTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_dashboard_requires_login(self):
        response = self.client.get('/billing/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
