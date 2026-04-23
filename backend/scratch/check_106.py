import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from patients.models import Patient
from medical_records.models import Visit

def check_patient():
    try:
        p = Patient.objects.get(patient_id='P-2026-106')
        print(f"Patient {p.patient_id} ({p.full_name}):")
        print(f"  is_hiv_patient = {p.is_hiv_patient}")
        
        visits = Visit.objects.filter(patient=p)
        print(f"  Visits: {visits.count()}")
        for v in visits:
            print(f"  - {v.visit_date}:")
            print(f"      Status: {v.status}")
            print(f"      Room: {v.current_room.code if v.current_room else 'None'}")
            print(f"      Diagnosis: {v.diagnosis.code if v.diagnosis else 'None'}")
    except Patient.DoesNotExist:
        print("Patient not found.")

if __name__ == '__main__':
    check_patient()
