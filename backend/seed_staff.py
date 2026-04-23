import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from staff.models import Department, StaffCategory, Position

def seed_data():
    # 1. Departments
    depts = [
        {'name': 'Rawat Jalan', 'code': 'RJ', 'description': 'Outpatient Department'},
        {'name': 'Laboratorium', 'code': 'LAB', 'description': 'Laboratory services'},
        {'name': 'Farmasi', 'code': 'FAR', 'description': 'Pharmacy and medication'},
        {'name': 'Administrasi', 'code': 'ADM', 'description': 'General administration'},
    ]
    for d in depts:
        Department.objects.get_or_create(name=d['name'], defaults=d)
    print("Departments seeded.")

    # 2. Categories
    cats = [
        {'name': 'Medis', 'description': 'Medical professionals (Doctors, Specialists)'},
        {'name': 'Paramedis', 'description': 'Nurses and medical technicians'},
        {'name': 'Non-Medis', 'description': 'Administrative and support staff'},
    ]
    for c in cats:
        StaffCategory.objects.get_or_create(name=c['name'], defaults=c)
    print("Categories seeded.")

    # 3. Positions
    positions = [
        {'name': 'Dokter Umum', 'description': 'General Practitioner'},
        {'name': 'Dokter Spesialis', 'description': 'Specialist Doctor'},
        {'name': 'Perawat Senior', 'description': 'Senior Nurse'},
        {'name': 'Perawat Junior', 'description': 'Junior Nurse'},
        {'name': 'Analis Lab', 'description': 'Laboratory Analyst'},
        {'name': 'Staf IT', 'description': 'IT Support Staff'},
    ]
    for p in positions:
        Position.objects.get_or_create(name=p['name'], defaults=p)
    print("Positions seeded.")

if __name__ == "__main__":
    seed_data()
