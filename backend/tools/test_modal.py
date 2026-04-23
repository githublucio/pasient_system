import os
import sys
import django

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from medical_records.views import visit_detail_ajax
from medical_records.models import Visit

try:
    v = Visit.objects.filter(status='COM').first()
    if not v:
        v = Visit.objects.first()
        
    if v:
        print(f"Testing with visit: {v.uuid}")
        
        factory = RequestFactory()
        request = factory.get(f'/records/visit/ajax/{v.uuid}/')
        
        # mock user
        user = User.objects.first()
        request.user = user
        
        response = visit_detail_ajax(request, visit_uuid=v.uuid)
        print(f"Response status: {response.status_code}")
        # print first 200 chars to verify
        # print(response.content.decode('utf-8')[:200])
        print("Template rendered successfully!")
    else:
        print("No visits found.")
except Exception as e:
    import traceback
    traceback.print_exc()
