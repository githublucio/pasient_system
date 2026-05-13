import os
import django

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from django.contrib.auth.models import User, Permission
from staff.models import StaffProfile, Department, StaffCategory, Position

def fix_jose():
    print("--- Memperbaiki User Jose ---")
    
    # 1. Pastikan User Jose ada
    user = User.objects.filter(username='jose').first()
    if not user:
        print("User 'jose' tidak ditemukan. Membuat baru...")
        user = User.objects.create_user('jose', 'jose@example.com', 'jose123')
    
    user.is_staff = True
    user.save()
    print(f"User ID: {user.id}")

    # 2. Pastikan Master Data ada
    dept, _ = Department.objects.get_or_create(name='Tuberculosis', defaults={'code': 'TB'})
    cat, _ = StaffCategory.objects.get_or_create(name='Medis')
    pos, _ = Position.objects.get_or_create(name='Dokter Umum')

    # 3. Pastikan StaffProfile ada
    profile, created = StaffProfile.objects.get_or_create(
        user=user,
        defaults={
            'staff_id': 'STAFF-JOSE',
            'department': dept,
            'category': cat,
            'position': pos,
            'is_active': True
        }
    )
    
    if not created:
        profile.department = dept
        profile.category = cat
        profile.position = pos
        profile.save()
        print("Profil staff diperbarui.")
    else:
        print("Profil staff baru dibuat.")

    # 4. Berikan izin akses menu
    permissions = Permission.objects.filter(codename__in=[
        'view_menu_medical_records', 'view_menu_specialist_tb', 'view_patient', 'add_visit', 'change_visit'
    ])
    user.user_permissions.set(permissions)
    
    print("--- Perbaikan Selesai ---")
    print("User: jose / Pass: jose123 (Jika baru dibuat)")

if __name__ == "__main__":
    fix_jose()
