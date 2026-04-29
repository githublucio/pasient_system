import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from patients.models import Patient
from printing.utils import generate_patient_assets

import gc

def regenerate_all():
    # Use only() to load minimal fields and iterator() to save memory
    patients = Patient.objects.only('uuid', 'patient_id').all().iterator()
    
    print(f"Starting memory-efficient regeneration...")
    
    from django.conf import settings
    
    for i, patient in enumerate(patients):
        try:
            # Check if assets already exist to save time/memory
            qr_path = os.path.join(settings.MEDIA_ROOT, 'qrcodes', f'qr_{patient.patient_id}.png')
            bar_path = os.path.join(settings.MEDIA_ROOT, 'barcodes', f'bar_{patient.patient_id}.png')
            
            if not os.path.exists(qr_path) or not os.path.exists(bar_path):
                generate_patient_assets(patient.uuid)
            
            if (i + 1) % 20 == 0:
                print(f"Processed {i + 1} patients...")
                gc.collect() # Force memory cleanup periodically
                
        except Exception as e:
            print(f"Error processing {patient.patient_id}: {e}")

    print("Regeneration complete.")

if __name__ == "__main__":
    regenerate_all()
