import os
import sys
import django

sys.path.append(r"d:\pasient_system\backend")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from medical_records.models import Visit
from django.test import Client
from django.contrib.auth.models import User

client = Client()
# Login as superuser
user = User.objects.filter(is_superuser=True).first()
client.force_login(user)

v = Visit.objects.first()
if v:
    response = client.get(f'/records/visit/ajax/{v.uuid}/')
    print(f"Status: {response.status_code}")
    if response.status_code == 500:
        print("ERROR 500!")
        from medical_records.views import visit_detail_ajax
        from django.test import RequestFactory
        factory = RequestFactory()
        req = factory.get(f'/records/visit/ajax/{v.uuid}/')
        req.user = user
        try:
            visit_detail_ajax(req, v.uuid)
            print("No exception raised by view directly!")
        except Exception as e:
            import traceback
            traceback.print_exc()
else:
    print("No visits.")
