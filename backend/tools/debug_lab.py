import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()
from laboratory.models import LabResult, LabRequest
from medical_records.models import Visit

for req in LabRequest.objects.select_related('visit__patient').order_by('-date_of_request')[:5]:
    res = getattr(req, 'result', None)
    print("Visit:", req.visit.patient.full_name)
    print("  Status:", req.status)
    print("  Tests:", [t.name for t in req.tests.all()])
    if res:
        keys = list(res.result_data.keys()) if res.result_data else "EMPTY_DICT"
        print("  result_data keys:", keys)
        snippet = (res.result_text or "")[:80]
        print("  result_text snippet:", snippet if snippet else "EMPTY")
        print("  attachment:", bool(res.attachment))
        print("  extra attachments:", res.attachments.count())
    else:
        print("  NO RESULT OBJECT")
    print()
