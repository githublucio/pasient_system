import os
import sys
import django

# Add the project root to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from django.contrib.auth.models import User
from medical_records.models import Visit

def test_visibility():
    users = User.objects.all()
    for user in users:
        try:
            print(f"Testing visibility for user: {user.username}")
            visits = Visit.objects.visible_to(user)
            count = visits.count()
            print(f"  Result: {count} visits visible.")
        except Exception as e:
            print(f"  ERROR for user {user.username}: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_visibility()
