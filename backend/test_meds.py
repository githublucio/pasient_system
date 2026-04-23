import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "clinic_core.settings")
django.setup()

from medical_records.models import EmergencyMedication, Visit

print("Total EmergencyMedications:", EmergencyMedication.objects.count())
for m in EmergencyMedication.objects.all():
    print(m.visit_id, m.medicine.name, m.quantity, m.given_by)
