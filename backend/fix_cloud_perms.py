import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from medical_records.models import Visit

def fix_permissions():
    print("Fixing permissions...")
    
    # 1. Get clinical permission
    content_type = ContentType.objects.get_for_model(Visit)
    perm, created = Permission.objects.get_or_create(
        codename='view_menu_medical_records',
        content_type=content_type,
        defaults={'name': 'Can see Medical Records menu'}
    )
    
    # 2. Ensure groups exist and have the permission
    groups_to_fix = ['Doctor', 'Nurse', 'IGD Doctor', 'IGD Nurse', 'Specialist']
    for group_name in groups_to_fix:
        group, created = Group.objects.get_or_create(name=group_name)
        if perm not in group.permissions.all():
            group.permissions.add(perm)
            print(f"Added view_menu_medical_records to group: {group_name}")

    # 3. FIX USERS: Ensure Melania and others are in the right group
    for user in User.objects.all():
        profile = getattr(user, 'staff_profile', None)
        if profile:
            cat_name = profile.category.name.upper()
            if cat_name == 'MEDIS':
                doctor_group = Group.objects.get(name='Doctor')
                if doctor_group not in user.groups.all():
                    user.groups.add(doctor_group)
                    print(f"Added user {user.username} to Doctor group")
            elif cat_name == 'PERAWAT':
                nurse_group = Group.objects.get(name='Nurse')
                if nurse_group not in user.groups.all():
                    user.groups.add(nurse_group)
                    print(f"Added user {user.username} to Nurse group")

    print("Permission fix complete.")

if __name__ == "__main__":
    fix_permissions()
