import os
import django
from django.test import Client
from django.contrib.auth import get_user_model

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "clinic_core.settings")
django.setup()

User = get_user_model()
admin = User.objects.get(username='admin')

client = Client()
client.force_login(admin)

# 1. Check Doctor Dashboard
response = client.get('/medical_records/doctor/')
print("DOCTOR DASHBOARD HTML snippet for 'Lab Result Ready':")
html = response.content.decode('utf-8')
if "Lab Result Ready" in html:
    print("SUCCESS: Found 'Lab Result Ready' badge in dashboard.")
    # Show snippet
    lines = html.split('\n')
    for i, line in enumerate(lines):
        if "Lab Result Ready" in line:
            print(f"Line {i+1}: {line.strip()}")
            break
else:
    print("WARNING: 'Lab Result Ready' not found in dashboard HTML. Maybe no completed labs?")

# Find a visit with a completed lab request
from medical_records.models import Visit
from laboratory.models import LabRequest

reqs = LabRequest.objects.filter(status='COMPLETED', tests__name__iexact='CBC')
if reqs.exists():
    req = reqs.first()
    visit = req.visit
    print(f"\nFound visit with CBC completed: {visit.uuid} for patient {visit.patient.full_name}")
    
    # Force visit to be in a doctor's room to show up correctly or just view the examination page
    response = client.get(f'/medical_records/examination/{visit.uuid}/')
    html = response.content.decode('utf-8')
    print("\nEXAMINATION HTML snippet for CBC table:")
    
    if "WBC" in html and "RBC" in html:
        print("SUCCESS: Found CBC parameters in examination sidebar.")
        lines = html.split('\n')
        start_idx = -1
        for i, line in enumerate(lines):
            if "WBC" in line:
                start_idx = i - 5
                break
        if start_idx != -1:
            print("\n".join(lines[start_idx:start_idx+20]))
    else:
        print("WARNING: CBC parameters not found in examination HTML.")
else:
    print("No COMPLETED CBC requests found to test.")
