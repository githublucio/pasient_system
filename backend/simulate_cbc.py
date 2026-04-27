import os
import sys
import django
from django.utils import timezone

sys.path.append(r'D:\pasient_system\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from medical_records.models import Visit
from patients.models import Patient
from django.contrib.auth.models import User
from laboratory.models import LabRequest, LabTest

def test_cbc_flow():
    # 1. Setup Patient
    admin_user = User.objects.filter(is_superuser=True).first()
    p, _ = Patient.objects.get_or_create(
        first_name="Test", last_name="CBC",
        defaults={'patient_id': 'TEST001', 'date_of_birth': '2000-01-01', 'gender': 'M'}
    )
    
    # 2. Setup Visit
    v = Visit.objects.create(
        patient=p,
        visit_date=timezone.now(),
        status='IP',
        lab_cbc=True,
        doctor=admin_user
    )
    print(f"Created Visit: {v.uuid}, lab_cbc={v.lab_cbc}")
    
    # 3. Simulate View Logic
    source_tag = 'OPD'
    is_lab_referral = False
    
    if v.lab_cbc or is_lab_referral:
        lab_req, created = LabRequest.objects.get_or_create(
            visit=v,
            defaults={
                'requesting_physician': admin_user,
                'source': source_tag
            }
        )
        print(f"Lab Request Created? {created}, ID={lab_req.id}, Status={lab_req.status}")
        
        if v.lab_cbc:
            try:
                cbc_test = LabTest.objects.get(name__iexact='CBC')
                lab_req.tests.add(cbc_test)
                print(f"Added CBC test to lab request {lab_req.id}")
            except LabTest.DoesNotExist:
                print("CBC Test DOES NOT EXIST!")
                
    # 4. Check Lab Dashboard Visibility
    today = timezone.localdate()
    pending_reqs = LabRequest.objects.filter(status='PENDING', visit__visit_date__date=today)
    print(f"Is this request in pending requests for today? {lab_req in pending_reqs}")

    pending_reqs_2 = LabRequest.objects.filter(date_of_request__date=today)
    print(f"Is this request in date_of_request for today? {lab_req in pending_reqs_2}")
    
    # Cleanup
    v.delete()
    if 'lab_req' in locals():
        lab_req.delete()

if __name__ == "__main__":
    test_cbc_flow()
