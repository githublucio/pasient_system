import os
import django
import sys

# Setup Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from django.contrib.auth.models import User
from staff.models import Department, StaffCategory, StaffProfile, Position

def setup_emergency_roles():
    print("--- Setting up Emergency Roles & Users ---")
    
    # 1. Create Department
    dept, created = Department.objects.get_or_create(
        code='IGD', 
        defaults={'name': 'Emergency (IGD)', 'description': 'Emergency Department Unit'}
    )
    if created:
        print(f"Created Department: {dept.name}")
    else:
        print(f"Department exists: {dept.name}")

    # 2. Get Categories
    cat_medis = StaffCategory.objects.get(name='Medis')
    cat_nurse = StaffCategory.objects.get(name='Paramedis')
    
    # 3. Get generic Position
    pos, _ = Position.objects.get_or_create(name='Staff', defaults={'description': 'Regular Staff'})

    # 4. Create Nurse User
    u_nurse, created = User.objects.get_or_create(
        username='nurse_emergency',
        defaults={
            'first_name': 'Emergency',
            'last_name': 'Nurse',
            'is_staff': True
        }
    )
    if created:
        u_nurse.set_password('emergency123')
        u_nurse.save()
        print("Created User: nurse_emergency")
    
    StaffProfile.objects.get_or_create(
        user=u_nurse,
        defaults={
            'staff_id': 'STF-NR-001',
            'department': dept,
            'category': cat_nurse,
            'position': pos
        }
    )

    # 5. Create Doctor User
    u_doctor, created = User.objects.get_or_create(
        username='doctor_emergency',
        defaults={
            'first_name': 'Emergency',
            'last_name': 'Doctor',
            'is_staff': True
        }
    )
    if created:
        u_doctor.set_password('emergency123')
        u_doctor.save()
        print("Created User: doctor_emergency")
    
    StaffProfile.objects.get_or_create(
        user=u_doctor,
        defaults={
            'staff_id': 'STF-DR-001',
            'department': dept,
            'category': cat_medis,
            'position': pos
        }
    )

    print("--- Setup Complete! ---")

if __name__ == "__main__":
    setup_emergency_roles()
