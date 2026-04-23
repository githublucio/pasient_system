import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from medical_records.models import Visit

visit_uuid = '93eb794a-8a9c-4f4a-ab1d-2bbe6b55e538'

try:
    visit = Visit.objects.get(uuid=visit_uuid)
    print(f"Visit Doctor: {visit.doctor}")
    print(f"Logs count: {visit.logs.count()}")
    for log in visit.logs.all():
        print(f"Log: {log.action}, Performed By: {log.performed_by}")
        
except Exception as e:
    print(f"Error: {e}")
