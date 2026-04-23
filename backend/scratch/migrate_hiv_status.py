import os
import sys
import django

# Add the project root to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from medical_records.models import Visit, Diagnosis
from patients.models import Patient
from django.db.models import Q

def migrate_hiv_status():
    print("Starting HIV patient tagging migration...")
    
    # 1. Identify all HIV-related diagnosis codes/names
    hiv_diags = Diagnosis.objects.filter(
        Q(code__icontains='B20') | 
        Q(code__icontains='B24') | 
        Q(name__icontains='HIV')
    )
    hiv_ids = [d.id for d in hiv_diags]
    print(f"Tracking {len(hiv_ids)} HIV-related ICD-10 codes.")

    # 2. Find visits with HIV diagnoses or in the HIV room
    hiv_visits = Visit.objects.filter(
        Q(current_room__code__in=['HIV', 'AIDS']) |
        Q(diagnosis_id__in=hiv_ids) |
        Q(secondary_diagnoses__id__in=hiv_ids)
    ).distinct()
    
    # 3. Extract unique patients from these visits
    patient_ids = hiv_visits.values_list('patient_id', flat=True).distinct()
    
    # 4. Update the patients
    patients_to_update = Patient.objects.filter(pk__in=patient_ids, is_hiv_patient=False)
    count = patients_to_update.count()
    
    print(f"Found {count} patients needing HIV data isolation.")
    
    if count > 0:
        patients_to_update.update(is_hiv_patient=True)
        print(f"Successfully secured {count} patients.")
    else:
        print("No new patients to secure. System is up to date.")

if __name__ == '__main__':
    migrate_hiv_status()
