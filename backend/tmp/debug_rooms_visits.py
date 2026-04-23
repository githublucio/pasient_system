import os
import sys
import django
from django.utils import timezone

sys.path.append('d:/pasient_system/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from medical_records.models import Visit, Room

print("--- ALL ROOMS ---")
for r in Room.objects.all().order_by('order'):
    print(f"Name: {r.name} | Code: {r.code} | Order: {r.order}")

print("\n--- RECENT VISITS (TODAY) ---")
today = timezone.localdate()
recent_visits = Visit.objects.filter(visit_date__date=today).order_by('-visit_date')
print(f"Visits today: {recent_visits.count()}")
for v in recent_visits:
    print(f"Patient: {v.patient.full_name} | Room: {v.current_room.code if v.current_room else 'None'} | Status: {v.status} | Date: {v.visit_date}")

print("\n--- DOCTOR DASHBOARD FILTER ---")
waiting_visits = Visit.objects.filter(
    visit_date__date=today, 
    current_room__code__in=['ROOM_3', 'ROOM_4', 'ROOM_5', 'ROOM_6'],
    status__in=['SCH', 'IP']
)
print(f"Waiting count: {waiting_visits.count()}")
