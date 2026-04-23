"""
Script to create a test Nutrition (NUTRISI) department user.
Run with: python scratch/create_nutrisi_user.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')

import django
django.setup()

from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from staff.models import Department, StaffCategory, Position, StaffProfile

# ─── 1. Ensure Nutrisi Department exists ────────────────────────────
dept, _ = Department.objects.get_or_create(
    code='NUTRISI',
    defaults={
        'name': 'Nutrition / Nutrisaun',
        'description': 'Nutrition & Dietetics Department',
        'is_active': True,
    }
)
print(f"[OK] Department: {dept}")

# ─── 2. Ensure StaffCategory exists ─────────────────────────────────
category, _ = StaffCategory.objects.get_or_create(
    name='Medis',
    defaults={'description': 'Medical / Clinical Staff'}
)
print(f"[OK] Category: {category}")

# ─── 3. Ensure Position exists ───────────────────────────────────────
position, _ = Position.objects.get_or_create(
    name='Staff Klinik',
    defaults={'description': 'General Clinical Staff'}
)
print(f"[OK] Position: {position}")

# ─── 4. Create Django User ───────────────────────────────────────────
USERNAME   = 'nutrisi_doctor'
PASSWORD   = 'Nutrisi@2025'
FIRST_NAME = 'Dr. Nutrition'
LAST_NAME  = 'Test'

user, created = User.objects.get_or_create(username=USERNAME)
user.set_password(PASSWORD)
user.first_name = FIRST_NAME
user.last_name  = LAST_NAME
user.is_active  = True
user.is_staff   = False
user.save()
print(f"[OK] User: {user.username}  ({'created' if created else 'updated'})")

# ─── 5. Create/update StaffProfile ──────────────────────────────────
profile, _ = StaffProfile.objects.get_or_create(
    user=user,
    defaults={
        'staff_id':   'NTR-001',
        'department': dept,
        'category':   category,
        'position':   position,
    }
)
# Always update department to be safe
profile.department = dept
profile.category   = category
profile.position   = position
profile.is_active  = True
profile.save()
print(f"[OK] StaffProfile: {profile}")

# ─── 6. Assign required permissions ─────────────────────────────────
PERMS = [
    # Medical records access
    'medical_records.view_menu_specialist_nutrition',
    'medical_records.add_visit',
    'medical_records.change_visit',
    'medical_records.view_visit',
    'medical_records.view_menu_medical_records',
    # Patient view
    'patients.view_patient',
]

added = []
for perm_str in PERMS:
    app_label, codename = perm_str.split('.')
    try:
        perm = Permission.objects.get(codename=codename)
        user.user_permissions.add(perm)
        added.append(codename)
    except Permission.DoesNotExist:
        print(f"  [WARN] Permission not found: {perm_str}")
    except Permission.MultipleObjectsReturned:
        for p in Permission.objects.filter(codename=codename):
            user.user_permissions.add(p)
        added.append(codename)

print(f"[OK] Permissions assigned: {added}")

print("\n" + "="*55)
print("  TEST LOGIN CREDENTIALS")
print("="*55)
print(f"  URL      : http://127.0.0.1:8000/")
print(f"  Username : {USERNAME}")
print(f"  Password : {PASSWORD}")
print(f"  Home URL : /records/doctor/?room=NUTRISI")
print("="*55)
