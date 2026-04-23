import os
import sys
import django
from django.utils import timezone

sys.path.append('d:/pasient_system/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from medical_records.models import Visit, Room

print("--- ROOM LIST ---")
for r in Room.objects.all().order_by('order'):
    print(f"Code: '{r.code}' | Name: '{r.name}'")

print("\n--- VISITS TODAY ---")
today = timezone.localdate()
for v in Visit.objects.filter(visit_date__date=today):
    print(f"P: {v.patient.full_name} | Room: '{v.current_room.code if v.current_room else 'None'}' | Status: '{v.status}' | Date: {v.visit_date}")
