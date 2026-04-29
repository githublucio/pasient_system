import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from patients.models import Patient
from printing.utils import generate_patient_assets

def regenerate_all():
    patients = Patient.objects.all()
    count = patients.count()
    print(f"Starting regeneration for {count} patients...")
    
    for i, patient in enumerate(patients):
        try:
            generate_patient_assets(patient.uuid)
            if (i + 1) % 10 == 0:
                print(f"Processed {i + 1}/{count}...")
        except Exception as e:
            print(f"Error processing {patient.patient_id}: {e}")

    print("Regeneration complete.")

if __name__ == "__main__":
    regenerate_all()
