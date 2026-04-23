import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from medical_records.models import Room

ROOM_MAPPING = {
    'ROOM_1': 'Registration / Reception',
    'ROOM_2': 'Triage / Nursing',
    'ROOM_3': 'Consultation Room - Dr. Gema',
    'ROOM_4': 'Consultation Room - Dr. Flory',
    'ROOM_5': 'Consultation Room - Dr. Jenhy',
    'ROOM_6': 'Consultation Room - Dr. Melania',
    'ROOM_7': 'Laboratory',
    'ROOM_8': 'Pharmacy',
    'KIA': 'MCH (Maternal & Child Health)',
    'HIV': 'HIV / AIDS',
    'TB': 'TB (Tuberculosis)',
    'DENTAL': 'Dental Clinic',
    'NUTRISI': 'Nutrition Clinic',
    'RADIOLOGY': 'Radiology',
    'EMERGENCY': 'Emergency Room (ER)',
}

for code, new_name in ROOM_MAPPING.items():
    Room.objects.filter(code=code).update(name=new_name)
    print(f"Updated {code} to {new_name}")

# Also check for 'DOKTER' or 'IGD' codes if they exist separately
Room.objects.filter(code='DOKTER').update(name='Doctor Consultation')
Room.objects.filter(code='IGD').update(name='Emergency / IGD')
