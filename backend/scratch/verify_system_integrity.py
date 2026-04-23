import os
import sys
import django

# Setup path and Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from django.contrib.auth.models import User, Permission
from staff.models import StaffProfile, Department
from medical_records.models import Room, Visit

def verify_setup():
    print("--- VERIFICATION REPORT ---")
    
    # 1. Check Departments & Rooms
    codes = ['USG', 'DENTAL', 'KIA', 'TB', 'NUTRISI', 'HIV']
    print("\n[1] Checking Departments & Rooms:")
    for code in codes:
        room_exists = Room.objects.filter(code=code).exists()
        dept_exists = Department.objects.filter(code=code).exists()
        print(f"  - {code}: Room {'OK' if room_exists else 'MISSING'}, Dept {'OK' if dept_exists else 'MISSING'}")

    # 2. Check Users & Profiles
    users = ['usg_staff', 'dental_staff', 'kia_staff', 'tb_staff']
    print("\n[2] Checking Users & Profiles:")
    for username in users:
        try:
            u = User.objects.get(username=username)
            has_profile = hasattr(u, 'staff_profile')
            perms = u.user_permissions.all().values_list('codename', flat=True)
            
            # Target permission check
            target_perm = f"view_menu_specialist_{username.split('_')[0]}"
            has_target_perm = target_perm in perms
            
            print(f"  - {username}: Profile {'OK' if has_profile else 'MISSING'}, Permission ({target_perm}) {'OK' if has_target_perm else 'MISSING'}")
            
            if has_profile:
                profile = u.staff_profile
                print(f"    -> Dept: {profile.department.code}, Home URL: {profile.home_url}")
        except User.DoesNotExist:
            print(f"  - {username}: USER MISSING")

    # 3. Check for potential syntax errors in template (dry render check)
    print("\n[3] Template Integrity Check:")
    from django.template.loader import get_template
    try:
        get_template('base.html')
        get_template('medical_records/completed_list.html')
        get_template('laboratory/lab_result_form_comprehensive.html')
        print("  - All key templates render successfully (No syntax errors).")
    except Exception as e:
        print(f"  - TEMPLATE ERROR: {e}")

    print("\n--- END OF REPORT ---")

if __name__ == "__main__":
    verify_setup()
