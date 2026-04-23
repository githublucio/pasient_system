import os
import sys
import django

# Add the current directory to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from patients.models import Patient
from medical_records.models import Visit

patient_id = 'MD20266013'

try:
    patient = Patient.objects.get(patient_id=patient_id)
    print(f"Patient found: {patient.full_name} ({patient.patient_id})")
    
    hiv_visits = Visit.objects.filter(patient=patient, current_room__code='HIV')
    if hiv_visits.exists():
        print(f"STATUS: HIV PATIENT (Found {hiv_visits.count()} HIV visits)")
        for v in hiv_visits:
            print(f" - Visit on {v.visit_date.date()}")
    else:
        print("STATUS: NOT AN HIV PATIENT (No HIV visits found)")
        
except Patient.DoesNotExist:
    print(f"ERROR: Patient with ID {patient_id} not found.")
except Exception as e:
    print(f"ERROR: {str(e)}")
