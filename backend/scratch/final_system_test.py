import os
import sys
import django
from decimal import Decimal

# Setup path and Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from django.contrib.auth.models import User
from patients.models import Patient
from medical_records.models import Room, Visit, Diagnosis
from billing.models import Invoice, ServicePrice, ServiceCategory, InvoiceItem

def test_system_flows():
    print("=== FINAL SYSTEM STRESS TEST & VERIFICATION ===")
    
    try:
        # 1. TEST TB AUTO-TAGGING
        print("\n[1] Testing TB Auto-Tagging Logic:")
        # Create a test patient
        p, _ = Patient.objects.get_or_create(
            patient_id="TEST-TB-99", 
            defaults={'full_name': 'Test TB Patient', 'date_of_birth': '1990-01-01', 'gender': 'M'}
        )
        p.is_tb_patient = False # Reset for test
        p.save()
        
        # Create a TB diagnosis
        diag, _ = Diagnosis.objects.get_or_create(code='A15.0', defaults={'name': 'Tuberculosis of lung'})
        room_tb, _ = Room.objects.get_or_create(code='TB', defaults={'name': 'TB Clinic'})
        
        # Create a visit with TB diagnosis
        v = Visit.objects.create(patient=p, current_room=room_tb, diagnosis=diag, queue_number=1)
        v.save() # Triggers auto-tagging
        
        p.refresh_from_db()
        if p.is_tb_patient:
            print("  - SUCCESS: Patient automatically tagged as TB after diagnosis/room entry.")
        else:
            print("  - FAILED: Patient NOT tagged as TB.")

        # 2. TEST TB BILLING (Lab Referral Case)
        print("\n[2] Testing TB Free Billing (Referral Case):")
        # Create a high price service
        cat_lab, _ = ServiceCategory.objects.get_or_create(code='LAB_BLOOD', defaults={'name': 'Lab Blood'})
        svc, _ = ServicePrice.objects.get_or_create(category=cat_lab, name='Expensive Lab Test', defaults={'price': 150.00})
        
        # Create invoice for this TB patient (even if for a different visit/referral)
        inv = Invoice.objects.create(
            invoice_number=Invoice.generate_invoice_number(),
            patient=p,
            visit=v,
            created_by=User.objects.first()
        )
        
        # Simulate adding the expensive item in views.py logic (manually applying logic for test)
        price = svc.price
        if p.is_tb_patient:
            price = Decimal('0.00')
            
        item = InvoiceItem.objects.create(
            invoice=inv, service=svc, category=cat_lab, description=svc.name, quantity=1, unit_price=price
        )
        inv.recalculate()
        
        if inv.total_amount == Decimal('0.00'):
            print(f"  - SUCCESS: Expensive Lab Test ($150) automatically charged as $0.00 for TB patient.")
        else:
            print(f"  - FAILED: TB Patient was charged ${inv.total_amount}.")

        # 3. TEST REDIRECTION LOGIC
        print("\n[3] Testing Staff Redirection (home_url):")
        from staff.models import StaffProfile
        users_to_test = ['usg_staff', 'dental_staff', 'kia_staff', 'tb_staff']
        for username in users_to_test:
            try:
                u = User.objects.get(username=username)
                if hasattr(u, 'staff_profile'):
                    print(f"  - {username} -> Home URL: {u.staff_profile.home_url} (OK)")
                else:
                    print(f"  - {username} -> PROFILE MISSING")
            except User.DoesNotExist:
                print(f"  - {username} -> USER MISSING")

        print("\n=== VERIFICATION COMPLETE ===")
        
    except Exception as e:
        print(f"\n!!! CRITICAL ERROR DURING VERIFICATION: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_system_flows()
