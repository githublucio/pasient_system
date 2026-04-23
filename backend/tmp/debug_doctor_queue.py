import os
import sys
import django
from django.utils import timezone

sys.path.append('d:/pasient_system/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from medical_records.models import Visit, Room

print("--- SEARCHING FOR WAITING PATIENTS IN DOCTOR ROOMS ---")
waiting_visits = Visit.objects.filter(
    current_room__code__in=['ROOM_3', 'ROOM_4', 'ROOM_5', 'ROOM_6'],
    status__in=['SCH', 'IP']
).order_by('-visit_date')

print(f"Total found: {waiting_visits.count()}")
for v in waiting_visits:
    print(f"P: {v.patient.full_name} | Room: {v.current_room.code} | Status: {v.status} | Date: {v.visit_date} | Local Date Query: {v.visit_date.date() == timezone.localdate()}")

print(f"\n--- SETTINGS INFO ---")
print(f"TIME_ZONE: {django.conf.settings.TIME_ZONE}")
print(f"USE_TZ: {django.conf.settings.USE_TZ}")
print(f"Current local date: {timezone.localdate()}")
