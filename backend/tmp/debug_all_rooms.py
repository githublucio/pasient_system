import os
import sys
import django
from django.utils import timezone

sys.path.append('d:/pasient_system/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from medical_records.models import Visit, Room

print("--- VISITS IN DOCTOR ROOMS (ANY DATE) ---")
doctor_rooms = ['ROOM_3', 'ROOM_4', 'ROOM_5', 'ROOM_6']
visits = Visit.objects.filter(current_room__code__in=doctor_rooms)
print(f"Total count: {visits.count()}")
for v in visits:
    print(f"P: {v.patient.full_name} | Room: {v.current_room.code} | Status: {v.status} | Date: {v.visit_date}")

print("\n--- VISITS IN TRIAGE ROOM (ROOM_2) ---")
triage_visits = Visit.objects.filter(current_room__code='ROOM_2')
print(f"Total count: {triage_visits.count()}")
for v in triage_visits:
    print(f"P: {v.patient.full_name} | Status: {v.status} | Date: {v.visit_date}")
