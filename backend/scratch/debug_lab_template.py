import os
import django
from django.conf import settings
from django.template import Template, Context

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from laboratory.models import LabRequest, LabTest
from medical_records.models import Visit, Patient
import uuid

def debug_template():
    # Create a mock request and lab request
    user = User.objects.first()
    
    # Get a real LabRequest if possible
    lab_req = LabRequest.objects.first()
    
    if not lab_req:
        print("No LabRequest found in DB")
        return

    from laboratory.views import lab_result_input
    rf = RequestFactory()
    request = rf.get(f'/lab/result/{lab_req.uuid}/')
    request.user = user
    
    try:
        response = lab_result_input(request, lab_req.uuid)
        print("Template rendered successfully")
    except Exception as e:
        print(f"Error rendering template: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_template()
