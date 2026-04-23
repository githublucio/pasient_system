import os
import sys
import django
from django.utils import timezone

sys.path.append('d:/pasient_system/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from medical_records.models import Visit, Room

waiting_visits = Visit.objects.filter(
    current_room__code__in=['ROOM_3', 'ROOM_4', 'ROOM_5', 'ROOM_6'],
    status__in=['SCH', 'IP']
).order_by('-visit_date')

today = timezone.localdate()
print(f"DEBUG:")
print(f"Localdate: {today}")

for v in waiting_visits:
    print(f"P: {v.patient.full_name}")
    print(f"Visit DateTime: {v.visit_date}")
    print(f"Local Date: {v.visit_date.astimezone(timezone.get_current_timezone()).date()}")
    print(f"Is same as daily check? {v.visit_date.astimezone(timezone.get_current_timezone()).date() == today}")
