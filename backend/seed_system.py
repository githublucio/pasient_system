import os
import django

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from django.contrib.auth.models import User, Group, Permission
from staff.models import Department, StaffCategory, Position, StaffProfile
from medical_records.models import Room

def run_seed():
    print("--- Memulai Seeding System Dasar ---")
    
    # 1. Buat Superuser jika belum ada
    admin_user = User.objects.filter(username='admin').first()
    if not admin_user:
        admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("Admin user created (admin/admin123)")
    else:
        print("Admin user already exists.")

    # 2. Buat Departemen Dasar
    depts = [
        {'name': 'Rawat Jalan', 'code': 'RJ'},
        {'name': 'Tuberculosis', 'code': 'TB'},
        {'name': 'Laboratorium', 'code': 'LAB'},
        {'name': 'Farmasi', 'code': 'FAR'},
        {'name': 'KIA', 'code': 'KIA'},
    ]
    for d in depts:
        Department.objects.get_or_create(code=d['code'], defaults={'name': d['name']})
    print("Departments created.")

    # 3. Buat Kategori & Jabatan
    cat_medis, _ = StaffCategory.objects.get_or_create(name='Medis')
    cat_paramedis, _ = StaffCategory.objects.get_or_create(name='Paramedis')
    
    pos_dokter, _ = Position.objects.get_or_create(name='Dokter Umum')
    pos_perawat, _ = Position.objects.get_or_create(name='Perawat')
    print("Categories and Positions created.")

    # 4. Buat Ruangan Dasar
    rooms = [
        {'name': 'Triage', 'code': 'TRIAGE', 'order': 1},
        {'name': 'Consultation', 'code': 'DOKTER', 'order': 2},
        {'name': 'TB Room', 'code': 'TB', 'order': 3},
    ]
    for r in rooms:
        Room.objects.get_or_create(code=r['code'], defaults={'name': r['name'], 'order': r['order']})
    print("Rooms created.")

    # 5. Pastikan Admin & Jose punya profil
    adm_dept, _ = Department.objects.get_or_create(code='ADM', defaults={'name': 'Administrasi'})
    
    # Profil untuk Admin
    StaffProfile.objects.get_or_create(
        user=admin_user,
        defaults={
            'staff_id': 'STAFF-ADMIN',
            'department': adm_dept,
            'category': cat_paramedis,
            'position': pos_perawat,
            'is_active': True
        }
    )
    print("Admin profile ensured.")

    jose = User.objects.filter(username='jose').first()
    if not jose:
        jose = User.objects.create_user('jose', 'jose@example.com', 'jose123')
        jose.is_staff = True
        jose.save()
        print("User jose created.")

    tb_dept = Department.objects.get(code='TB')
    StaffProfile.objects.get_or_create(
        user=jose,
        defaults={
            'staff_id': 'STAFF-JOSE',
            'department': tb_dept,
            'category': cat_medis,
            'position': pos_dokter,
            'is_active': True
        }
    )

    # 6. Permissions
    permissions = Permission.objects.filter(codename__in=[
        'view_menu_medical_records', 'view_menu_specialist_tb', 'view_patient', 'add_visit', 'change_visit'
    ])
    jose.user_permissions.set(permissions)
    
    print("--- Seeding Selesai ---")

if __name__ == "__main__":
    run_seed()
