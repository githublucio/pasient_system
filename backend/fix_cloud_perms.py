import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from medical_records.models import Visit

def fix_permissions():
    print("Fixing permissions...")
    
    # 1. Ensure the 'view_menu_medical_records' permission exists
    content_type = ContentType.objects.get_for_model(Visit)
    perm, created = Permission.objects.get_or_create(
        codename='view_menu_medical_records',
        content_type=content_type,
        defaults={'name': 'Can see Medical Records menu'}
    )
    
    # 2. Assign it to common groups (Doctor, Nurse, etc.)
    groups_to_fix = ['Doctor', 'Nurse', 'IGD Doctor', 'IGD Nurse', 'Specialist']
    for group_name in groups_to_fix:
        group, created = Group.objects.get_or_create(name=group_name)
        if perm not in group.permissions.all():
            group.permissions.add(perm)
            print(f"Added view_menu_medical_records to group: {group_name}")
        else:
            print(f"Group {group_name} already has the permission.")

    print("Permission fix complete.")

if __name__ == "__main__":
    fix_permissions()
