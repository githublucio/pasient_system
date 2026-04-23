import os
import random
import uuid
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.models import User
from patients.models import Patient, Municipio, PostoAdministrativo, Suco, Aldeia, DailyQueue
from medical_records.models import Visit, Room, Diagnosis, VisitLog
from pharmacy.models import Medicine, Prescription, DispensedItem, StockEntry
from laboratory.models import LabRequest, LabResult, LabTest
from radiology.models import RadiologyRequest, RadiologyResult, RadiologyTest
from pathology.models import PathologyRequest, PathologyResult, PathologyTest
from billing.models import Invoice, InvoiceItem, Payment, ServicePrice, ServiceCategory

# Helper to get random geography
def get_random_geo():
    aldeia = Aldeia.objects.order_by('?').first()
    if not aldeia: return None, None, None, None
    suco = aldeia.suco
    posto = suco.posto
    muni = posto.municipio
    return muni, posto, suco, aldeia

def seed():
    print("--- TRUNCATING START ---")
    Payment.objects.all().delete()
    InvoiceItem.objects.all().delete()
    Invoice.objects.all().delete()
    DispensedItem.objects.all().delete()
    Prescription.objects.all().delete()
    LabResult.objects.all().delete()
    LabRequest.objects.all().delete()
    RadiologyResult.objects.all().delete()
    RadiologyRequest.objects.all().delete()
    PathologyResult.objects.all().delete()
    PathologyRequest.objects.all().delete()
    VisitLog.objects.all().delete()
    Visit.objects.all().delete()
    Patient.objects.all().delete()
    DailyQueue.objects.all().delete()
    print("--- TRUNCATING DONE ---")

    # Ensure some Medicines exist
    medicines_data = [
        ('Paracetamol', '500mg', 'TABLET', 'PAR500'),
        ('Amoxicillin', '500mg', 'CAPSULE', 'AMX500'),
        ('Ibuprofen', '400mg', 'TABLET', 'IBU400'),
        ('Salbutamol', '2mg', 'TABLET', 'SAL2'),
        ('Omeprazole', '20mg', 'CAPSULE', 'OME20'),
        ('Ciprofloxacin', '500mg', 'TABLET', 'CIP500'),
        ('Metformin', '500mg', 'TABLET', 'MET500'),
        ('Amlodipine', '5mg', 'TABLET', 'AML5'),
        ('Azithromycin', '500mg', 'TABLET', 'AZI500'),
        ('Cetirizine', '10mg', 'TABLET', 'CET10'),
    ]
    
    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    
    for name, strength, form, code in medicines_data:
        med, created = Medicine.objects.get_or_create(
            code=code,
            defaults={'name': name, 'strength': strength, 'form': form, 'stock': 1000}
        )
        if created:
            # Add initial stock
            StockEntry.objects.create(
                medicine=med,
                quantity=1000,
                remaining_qty=1000,
                purchase_date=timezone.now().date(),
                created_by=admin_user
            )

    # Ensure Service Prices for Invoices
    general_cat, _ = ServiceCategory.objects.get_or_create(code='GEN', defaults={'name': 'General Services', 'is_active': True})
    ServicePrice.objects.get_or_create(code='CONS', defaults={'name': 'Consultation', 'price': 5.00, 'category': general_cat})
    ServicePrice.objects.get_or_create(code='REG', defaults={'name': 'Registration', 'price': 2.00, 'category': general_cat})

    # Dummy Patients
    names = [
        ('Maria', 'Soares'), ('Jose', 'Pinto'), ('Antonio', 'da Costa'), 
        ('Filomena', 'Amaral'), ('Domingos', 'Belo'), ('Rosa', 'Martins'),
        ('Joao', 'Guterres'), ('Lucia', 'Pereira'), ('Augusto', 'Ximenes'),
        ('Teresa', 'da Silva')
    ]
    genders = ['F', 'M', 'M', 'F', 'M', 'F', 'M', 'F', 'M', 'F']
    
    rooms = list(Room.objects.all())
    diagnoses = list(Diagnosis.objects.all())
    doctors = list(User.objects.all())

    for i in range(10):
        first_name, last_name = names[i]
        full_name = f"{first_name} {last_name}"
        p_id = f"P-2026-{100+i}"
        dob = timezone.now().date() - timezone.timedelta(days=random.randint(365*5, 365*70))
        
        muni, posto, suco, aldeia = get_random_geo()
        
        patient = Patient.objects.create(
            patient_id=p_id,
            full_name=full_name,
            date_of_birth=dob,
            gender=genders[i],
            municipio=muni,
            posto_administrativo=posto,
            suco=suco,
            aldeia=aldeia,
            phone_number=f"7700{1000+i}",
            registration_fee=2.00
        )
        print(f"Created Patient: {full_name}")

        # Visit for Today
        # Get Queue Number
        queue, _ = DailyQueue.objects.get_or_create(date=timezone.now().date())
        q_num = queue.get_next_number()
        
        room = rooms[i % len(rooms)] if rooms else None
        doctor = random.choice(doctors) if doctors else admin_user
        diag = random.choice(diagnoses) if diagnoses else None

        visit = Visit.objects.create(
            patient=patient,
            doctor=doctor,
            queue_number=q_num,
            current_room=room,
            visit_fee=5.00,
            complaint=random.choice(["Kof", "Isin Manas", "Uat Malirin", "Ulun Moras", "Kabaas Moras"]),
            bp_sys=random.randint(110, 140),
            bp_dia=random.randint(70, 95),
            spo2=random.randint(95, 100),
            pulse=random.randint(60, 100),
            rr=random.randint(16, 24),
            temp=Decimal(f"{random.uniform(36.0, 39.0):.1f}"),
            weight=Decimal(f"{random.uniform(10.0, 90.0):.1f}"),
            diagnosis=diag,
            clinical_notes="Patient presented with mild symptoms. Vital signs stable.",
            status='COM' if i < 7 else 'IP'
        )

        # Visit Log
        VisitLog.objects.create(visit=visit, action='CHECK_IN', performed_by=admin_user, room=room)
        VisitLog.objects.create(visit=visit, action='TRIAGE', performed_by=admin_user, room=room)
        VisitLog.objects.create(visit=visit, action='EXAMINATION', performed_by=doctor, room=room)

        # Pharmacy (5 visits)
        if i < 5:
            rx = Prescription.objects.create(
                visit=visit,
                prescription_text="R/ Paracetamol 500mg No. X\nS 3 dd 1 tab\n\nR/ Amoxicillin 500mg No. XV\nS 3 dd 1 cap",
                doctor=doctor,
                dispensing_status='DISPENSED',
                dispensed_by=admin_user,
                dispensed_at=timezone.now()
            )
            # Add dispensed items
            p_med = Medicine.objects.get(code='PAR500')
            a_med = Medicine.objects.get(code='AMX500')
            DispensedItem.objects.create(prescription=rx, medicine=p_med, quantity=10, dosage_instructions="3x1 tab after meal")
            DispensedItem.objects.create(prescription=rx, medicine=a_med, quantity=15, dosage_instructions="3x1 cap after meal")
            VisitLog.objects.create(visit=visit, action='PRESCRIPTION', performed_by=doctor)
            VisitLog.objects.create(visit=visit, action='DISPENSED', performed_by=admin_user)

        # Laboratory (3 visits)
        if 5 <= i < 8:
            l_req = LabRequest.objects.create(
                visit=visit,
                lab_no=f"LAB-{100+i}",
                patient_type='OUT',
                urgency='NORMAL',
                requesting_physician=doctor,
                status='COMPLETED'
            )
            tests = list(LabTest.objects.order_by('?')[:3])
            l_req.tests.set(tests)
            LabResult.objects.create(
                lab_request=l_req,
                result_text="WBC: 7.5 x10^9/L\nHgB: 13.5 g/dL\nPLT: 250 x10^9/L",
                verified_by=admin_user,
                completed_at=timezone.now()
            )
            VisitLog.objects.create(visit=visit, action='LAB_REQUEST', performed_by=doctor)
            VisitLog.objects.create(visit=visit, action='LAB_RESULT', performed_by=admin_user)

        # Radiology (2 visits)
        if 8 <= i < 10:
            rad_req = RadiologyRequest.objects.create(
                visit=visit,
                requesting_physician=doctor,
                status='COMPLETED'
            )
            rad_tests = list(RadiologyTest.objects.order_by('?')[:1])
            rad_req.tests.set(rad_tests)
            RadiologyResult.objects.create(
                radiology_request=rad_req,
                findings="Normal heart size. Lungs clear.",
                impression="No acute cardiopulmonary disease.",
                verified_by=admin_user,
                completed_at=timezone.now()
            )
            VisitLog.objects.create(visit=visit, action='RAD_REQUEST', performed_by=doctor)
            VisitLog.objects.create(visit=visit, action='RAD_RESULT', performed_by=admin_user)

        # Invoice
        inv_num = Invoice.generate_invoice_number()
        invoice = Invoice.objects.create(
            invoice_number=inv_num,
            visit=visit,
            patient=patient,
            subtotal=7.00,
            total_amount=7.00,
            status='PAID' if i < 7 else 'UNPAID',
            created_by=admin_user
        )
        # Add items
        c_svc = ServicePrice.objects.get(code='CONS')
        r_svc = ServicePrice.objects.get(code='REG')
        InvoiceItem.objects.create(invoice=invoice, description="Consultation Fee", quantity=1, unit_price=Decimal("5.00"), service=c_svc)
        InvoiceItem.objects.create(invoice=invoice, description="Registration Fee", quantity=1, unit_price=Decimal("2.00"), service=r_svc)
        
        if i < 7:
            Payment.objects.create(
                invoice=invoice,
                amount=7.00,
                payment_method='CASH',
                received_by=admin_user
            )
            invoice.amount_paid = 7.00
            invoice.save()

    print(f"DONE seeding 10 patients.")

if __name__ == "__main__":
    seed()
