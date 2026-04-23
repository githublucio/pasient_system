import os
import sys
import django
from django.utils import timezone

sys.path.append('d:/pasient_system/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from medical_records.models import Visit, Room

print("--- RECENT VISITS (LAST 20) ---")
for v in Visit.objects.all().order_by('-visit_date')[:20]:
    print(f"P: {v.patient.full_name} | Room: '{v.current_room.code if v.current_room else 'None'}' | Status: '{v.status}' | Date: {v.visit_date}")
