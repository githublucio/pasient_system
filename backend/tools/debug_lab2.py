import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()
import json
from laboratory.models import LabResult, LabRequest

# Inspect first completed result in full
req = LabRequest.objects.filter(status='COMPLETED').select_related('result').first()
if req and hasattr(req, 'result') and req.result:
    res = req.result
    print("=== FULL result_data ===")
    print(json.dumps(res.result_data, indent=2, default=str))
else:
    print("No completed result found")
