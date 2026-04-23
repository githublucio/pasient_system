from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from .models import StaffProfile

@receiver(post_save, sender=StaffProfile)
def sync_user_groups(sender, instance, created, **kwargs):
    """
    Automatically adds the user to a Django Group based on their StaffCategory.
    Mapping is based on Category Name.
    """
    user = instance.user
    category_name = instance.category.name.upper()

    # Define potential mappings
    group_map = {
        'DOKTER': 'Doctor',
        'DOCTOR': 'Doctor',
        'PERAWAT': 'Nurse',
        'NURSE': 'Nurse',
        'PHARMACIST': 'Pharmacist',
        'PHARMACISTA': 'Pharmacist',
        'FARMASI': 'Pharmacist',
        'ADMIN': 'Admin',
        'RECEPTIONIST': 'Receptionist'
    }

    # Clean up and find match
    matched_group_name = None
    for key, val in group_map.items():
        if key in category_name:
            matched_group_name = val
            break

    if matched_group_name:
        group, _ = Group.objects.get_or_create(name=matched_group_name)
        # Clear existing clinic roles if needed, then add the new one
        # For simplicity, we just add the new group
        user.groups.add(group)
        
        # If it's an Admin, also set is_staff
        if matched_group_name == 'Admin':
            user.is_staff = True
            user.save()
