import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from medical_records.models import Visit
from medical_records.views import enrich_visit_lab_results

try:
    v = Visit.objects.first()
    if v:
        enrich_visit_lab_results(v)
        res = "OK"
    else:
        res = "NO VISITS"
except Exception as e:
    res = f"ERROR: {type(e).__name__} - {e}"

print(res)
