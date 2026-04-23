import os
import django
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "clinic_core.settings")
django.setup()

from medical_records.models import EmergencyMedication, EmergencyObservation

now = timezone.now()
ten_mins_ago = now - timedelta(minutes=15)

recent_meds = EmergencyMedication.objects.filter(given_at__gt=ten_mins_ago)
print("Recent Meds:", recent_meds.count())
for m in recent_meds:
    print(m.visit_id, m.medicine.name, m.quantity, m.given_at)

recent_obs = EmergencyObservation.objects.filter(check_time__gt=ten_mins_ago)
print("Recent Obs:", recent_obs.count())
for o in recent_obs:
    print(o.visit_id, o.bp_sys, o.check_time)
