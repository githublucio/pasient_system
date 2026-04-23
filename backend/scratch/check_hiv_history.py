import os
import sys
import django

# Add the project root to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from medical_records.models import Visit
from django.contrib.auth.models import User

def check_hiv_visits():
    patient_ids = ['P-2026-102', 'P-2026-108', 'MD20266015']
    visits = Visit.objects.filter(patient__patient_id__in=patient_ids).select_related('patient', 'current_room')
    
    print("All visits for selected patients:")
    for v in visits:
        room_code = v.current_room.code if v.current_room else "None"
        print(f"- {v.patient.full_name} ({v.patient.patient_id}):")
        print(f"    Room: {room_code}")
        print(f"    Status: {v.status}")
        print(f"    Date: {v.visit_date}")

    # Now check what the 'admin' or typical user sees
    admin_user = User.objects.filter(is_superuser=True).first()
    if admin_user:
        print(f"\nVisits visible to admin ({admin_user.username}):")
        visible_visits = Visit.objects.visible_to(admin_user).filter(patient__patient_id__in=patient_ids)
        for v in visible_visits:
             print(f"- {v.patient.full_name} (Status: {v.status})")

if __name__ == '__main__':
    check_hiv_visits()
