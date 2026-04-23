import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from medical_records.models import Room

def create_emergency_room():
    # Attempt to create the EMERGENCY room if it doesn't exist
    room, created = Room.objects.get_or_create(
        code='EMERGENCY',
        defaults={
            'name': 'Emergency / IGD',
            'description': 'Emergency Room for critical cases requiring immediate medical attention.',
            'order': 99 # High order for placement
        }
    )
    if created:
        print(f"Successfully created room: {room.name} ({room.code})")
    else:
        print(f"Room {room.code} already exists.")

if __name__ == "__main__":
    create_emergency_room()
