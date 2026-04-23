
from medical_records.models import Visit
from django.contrib.auth.models import User

hiv_user = User.objects.filter(staff_profile__department__code='HIV').first()
if not hiv_user:
    print("No HIV user found for testing.")
else:
    print(f"Testing for user: {hiv_user.username}")
    
    # Simulate the logic in department_completed_list
    visits = Visit.objects.visible_to(hiv_user).filter(status='COM')
    
    is_hiv_staff = hasattr(hiv_user, 'staff_profile') and hiv_user.staff_profile.is_hiv_staff
    
    # Default behavior for HIV staff in the view now
    if is_hiv_staff:
        # The view now sets dept = 'HIV' which triggers:
        visits = visits.filter(patient__is_hiv_patient=True)
        
    print(f"Visits visible to HIV Staff: {visits.count()}")
    for v in visits:
        print(f"- {v.patient.full_name} ({v.visit_date.date()})")
