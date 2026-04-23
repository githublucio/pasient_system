import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from patients.models import Patient
from medical_records.models import Visit

patient_id = 'MD20266013'

try:
    patient = Patient.objects.get(patient_id=patient_id)
    visits = Visit.objects.filter(patient=patient, current_room__code='HIV')
    
    for v in visits:
        print(f"Visit ID: {v.uuid}")
        print(f"Date: {v.visit_date}")
        print(f"Diagnosis: {v.diagnosis}")
        print(f"Clinical Notes: {v.clinical_notes}")
        print("-" * 20)
        
except Exception as e:
    print(f"Error: {e}")
