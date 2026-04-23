import os
import django
import sys
from datetime import date

# Setup Django environment
sys.path.append('d:\\pasient_system\\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from patients.models import Patient, DailyQueue
from medical_records.models import Visit, Room
from django.utils import timezone

def create_test_data():
    today = date.today()
    triage_room = Room.objects.filter(code='ROOM_2').first()
    
    if not triage_room:
        print("Error: ROOM_2 not found. Please run populate_rooms.py first.")
        return

    # Get or create daily queue
    queue, _ = DailyQueue.objects.get_or_create(date=today, department='General')

    patients_data = [
        {"name": "Joao Silva", "id": "MD20260001", "gender": "M", "dob": "1994-05-15", "fee": "5.00"},
        {"name": "Maria Costa", "id": "MD20260002", "gender": "F", "dob": "2001-11-20", "fee": "0.00"},
    ]

    for data in patients_data:
        # Create Patient
        patient, created = Patient.objects.get_or_create(
            patient_id=data['id'],
            defaults={
                'full_name': data['name'],
                'gender': data['gender'],
                'date_of_birth': data['dob'],
            }
        )
        
        if created:
            print(f"Created Patient: {data['name']} ({data['id']})")
        else:
            print(f"Patient already exists: {data['name']}")

        # Create Visit (Check-in to Room 2)
        visit_exists = Visit.objects.filter(patient=patient, visit_date__date=today).exists()
        if not visit_exists:
            q_num = queue.get_next_number()
            Visit.objects.create(
                patient=patient,
                current_room=triage_room,
                queue_number=q_num,
                visit_fee=data['fee'],
                status='SCH',
                complaint="Pusing dan demam (Test Case)"
            )
            print(f"Checked-in {data['name']} to Room 2 (Triage). Queue: #{q_num}")
        else:
            print(f"Visit already exists for {data['name']} today.")

if __name__ == "__main__":
    create_test_data()
