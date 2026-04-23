import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
sys.path.append('d:/pasient_system/backend')
django.setup()

from django.test import RequestFactory
from medical_records.views import perform_examination
from medical_records.models import Visit
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage

def debug_view():
    factory = RequestFactory()
    # Find any visit to test
    visit = Visit.objects.first()
    if not visit:
        print("No visit found to test.")
        return
    
    # Create a user for authentication
    user = User.objects.filter(is_superuser=True).first()
    
    # Simulate a GET request
    request = factory.get(f'/records/examination/{visit.uuid}/')
    request.user = user
    
    # Add messages support
    setattr(request, '_messages', FallbackStorage(request))
    
    try:
        response = perform_examination(request, str(visit.uuid))
        print(f"Status: {response.status_code}")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_view()
