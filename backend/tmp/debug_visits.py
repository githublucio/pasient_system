import os
import sys
import django
from django.utils import timezone

sys.path.append('d:/pasient_system/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from medical_records.models import Visit, Room

print("--- DEBUGGING VISITS ---")
today = timezone.localdate()
print(f"Today (localdate): {today}")

all_visits = Visit.objects.all().order_by('-visit_date')[:10]
for v in all_visits:
    print(f"Visit: {v.uuid} | Date: {v.visit_date} | Local Date: {v.visit_date.astimezone(timezone.get_current_timezone()).date()} | Room: {v.current_room.code if v.current_room else 'None'} | Status: {v.status}")

print("\n--- ROOMS ---")
for r in Room.objects.all():
    print(f"Room: {r.name} | Code: {r.code}")

print("\n--- FILTERED VISITS (DOCTOR) ---")
waiting_visits = Visit.objects.filter(
    visit_date__date=today, 
    current_room__code__in=['ROOM_3', 'ROOM_4', 'ROOM_5', 'ROOM_6'],
    status__in=['SCH', 'IP']
)
print(f"Count: {waiting_visits.count()}")
for v in waiting_visits:
    print(f"Waiting: {v.patient.full_name} | Room: {v.current_room.code}")
