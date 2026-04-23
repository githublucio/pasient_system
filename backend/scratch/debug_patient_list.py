from patients.models import Patient
from medical_records.models import Visit

hiv_patients = Patient.objects.filter(is_hiv_patient=True)
print(f"Total HIV Patients (is_hiv_patient=True): {hiv_patients.count()}")

for p in hiv_patients:
    has_hiv_visit = Visit.objects.filter(patient=p, current_room__code='HIV').exists()
    all_rooms = Visit.objects.filter(patient=p).values_list('current_room__code', flat=True).distinct()
    print(f"- {p.full_name}")
    print(f"  UUID: {p.uuid}")
    print(f"  Has HIV Visit: {has_hiv_visit}")
    print(f"  All visited rooms: {list(all_rooms)}")
