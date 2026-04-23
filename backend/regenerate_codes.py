import os
import django
import sys

# Add project directory to python path
sys.path.append(r'd:\pasient_system\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from patients.models import Patient
from printing.utils import generate_patient_assets

patients = Patient.objects.all()
for p in patients:
    print(f"Regenerating assets for {p.patient_id} ({p.full_name})...")
    # By forcing generate_patient_assets, it will overwrite the existing ones
    generate_patient_assets(p.uuid)
    
print("All patient QR codes and Barcodes have been updated!")
