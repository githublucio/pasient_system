from django.contrib.auth.models import User, Group

try:
    g_doctor = Group.objects.get(name='Doctor')
    u_doctor = User.objects.get(username='doctor_emergency')
    u_doctor.groups.add(g_doctor)
    print('Added doctor_emergency to Doctor group')
except Exception as e:
    print('Error with doctor:', e)

try:
    g_nurse = Group.objects.get(name='Nurse')
    u_nurse = User.objects.get(username='nurse_emergency')
    u_nurse.groups.add(g_nurse)
    print('Added nurse_emergency to Nurse group')
except Exception as e:
    print('Error with nurse:', e)
