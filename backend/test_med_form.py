import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "clinic_core.settings")
django.setup()

from medical_records.forms import EmergencyMedicationForm
from pharmacy.models import Medicine

# check if any medicine has stock
m = Medicine.objects.filter(is_active=True, stock__gt=0).first()
print("Medicine with stock:", m)

form = EmergencyMedicationForm(data={
    "quantity": "1",
    "admin_type": "ORAL",
    "dosage_instruction": "1 tab",
    "medicine": m.id if m else ""
})
print("Is Valid:", form.is_valid())
if not form.is_valid():
    print("Errors:", form.errors)
