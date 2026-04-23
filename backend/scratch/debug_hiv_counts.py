
from patients.models import Patient
from medical_records.models import Visit
from django.db.models import Count

hiv_patients = Patient.objects.filter(is_hiv_patient=True)
hiv_count = hiv_patients.count()
visit_count = Visit.objects.filter(patient__is_hiv_patient=True, status='COM').count()

print(f"HIV Patients in Database: {hiv_count}")
print(f"Total Completed Visits for HIV Patients: {visit_count}")

print("\nBreakdown per Patient:")
for p in hiv_patients:
    v_count = Visit.objects.filter(patient=p, status='COM').count()
    print(f"- {p.full_name} ({p.patient_id}): {v_count} completed visits")

# Check if there are visits for non-HIV patients that might be showing up?
# (The view filters by patient__is_hiv_patient=True, so that's unlikely unless the flag is wrong)
