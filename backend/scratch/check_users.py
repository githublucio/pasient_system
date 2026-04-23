import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'clinic_core.settings'
django.setup()

from django.contrib.auth.models import User, Permission

print("ALL ACTIVE USERS AND THEIR add_visit STATUS:")
print("-" * 60)
for u in User.objects.filter(is_active=True).order_by('username'):
    has_perm = u.is_superuser or u.user_permissions.filter(codename='add_visit').exists()
    dept = ''
    try:
        dept = u.staff_profile.department.code
    except Exception:
        dept = 'NO PROFILE'
    status = "YES" if has_perm else " NO"
    print(f"  [{status}]  {u.username:<20}  dept={dept}")
