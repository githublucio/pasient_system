import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from django.contrib.auth.models import User
from staff.models import StaffProfile

for u in User.objects.all():
    profile = getattr(u, 'staff_profile', None)
    dept = profile.department.code if profile and profile.department else 'N/A'
    print(f"User: {u.username}, Superuser: {u.is_superuser}, Dept: {dept}")
    u.set_password('admin')
    u.save()
print("Passwords reset to 'admin'")
