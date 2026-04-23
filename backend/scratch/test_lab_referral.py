import os
import django
import sys

# Setup django environment
sys.path.append('d:\\pasient_system\\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from medical_records.models import Visit, Room
from laboratory.models import LabRequest

def test_referral_logic():
    # 1. Find a test visit and the Lab room
    visit = Visit.objects.latest('visit_date')
    lab_room = Room.objects.get(code='ROOM_7')
    
    print(f"Testing with Visit: {visit.uuid} (Patient: {visit.patient.full_name})")
    print(f"Target Room: {lab_room.name} (Code: {lab_room.code})")
    
    # Simulate the logic in views.py
    referral_target = lab_room
    
    # line 660 logic
    is_lab_referral = referral_target and (
        'LAB' in referral_target.name.upper() or 
        'LAB' in referral_target.code.upper() or 
        referral_target.code in ['LAB', 'ROOM_7']
    )
    
    print(f"Is Lab Referral Detected: {is_lab_referral}")
    
    if is_lab_referral:
        print("Attempting to create LabRequest...")
        from laboratory.models import LabRequest
        lab_req, created = LabRequest.objects.get_or_create(
            visit=visit,
            defaults={'requesting_physician': visit.doctor}
        )
        print(f"LabRequest Created: {created}, UUID: {lab_req.uuid}")
    else:
        print("FAIL: Lab referral was NOT detected.")

if __name__ == "__main__":
    test_referral_logic()
