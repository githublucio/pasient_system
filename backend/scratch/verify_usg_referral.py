import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from medical_records.models import Visit, Room
from patients.models import Patient
from django.contrib.auth.models import User

# 1. Setup minimal data
patient = Patient.objects.first()
doctor = User.objects.first()
emergency_room = Room.objects.filter(code='EMERGENCY').first()
usg_room = Room.objects.filter(code='USG').first()

if not emergency_room or not usg_room:
    print("Error: Required rooms not found.")
    exit(1)

# 2. Simulate EMERGENCY Visit
visit = Visit.objects.create(
    patient=patient,
    current_room=emergency_room,
    queue_number=999,
    doctor=doctor,
    status='IP',
    source='IGD' # Set manually as it would be from registration
)

print(f"Initial Visit Source: {visit.source}")

# 3. Simulate Referral to USG via logic (Simplified)
# In views.py, if is_emergency is True (room is IGD), source becomes IGD
is_emergency = visit.current_room.code in ['IGD', 'EMERGENCY']
source_tag = 'IGD' if is_emergency else 'OPD'

if visit.source != source_tag:
    visit.source = source_tag
    visit.save()

print(f"Unified Source Tag: {source_tag}")
print(f"Final Visit Source: {visit.source}")

# 4. Check if USG is in all_clinical_rooms (Simulated view check)
all_clinical_rooms = [
    'DOKTER', 'KIA', 'HIV', 'TB', 'DENTAL', 'NUTRISI', 'USG',
    'ROOM_3', 'ROOM_4', 'ROOM_5', 'ROOM_6',
]
print(f"Is USG in Clinical Rooms List? {'USG' in all_clinical_rooms}")

# Clean up
visit.delete()
