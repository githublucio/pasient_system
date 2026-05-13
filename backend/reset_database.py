import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from django.contrib.auth.models import User
from patients.models import Patient
from medical_records.models import Visit
from staff.models import StaffProfile, Department, StaffCategory

def full_reset_and_setup():
    print("--- Memulai Pembersihan Total ---")
    # Hapus semua data
    Visit.objects.all().delete()
    Patient.objects.all().delete()
    StaffProfile.objects.all().delete()
    User.objects.all().delete()
    print("Database sudah dikosongkan.")

    # 1. Buat Superuser (Admin)
    print("Membuat Admin baru...")
    admin = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    
    # 2. Buat Departemen TB (Jika belum ada)
    tb_dept, _ = Department.objects.get_or_create(name='Tuberculosis', code='TB')
    doc_cat, _ = StaffCategory.objects.get_or_create(name='Dokter')

    # 3. Buat User Jose
    print("Membuat user Jose...")
    jose = User.objects.create_user('jose', 'jose@example.com', 'jose123')
    jose.is_staff = True
    jose.save()
    
    # Berikan Jose Staff Profile di departemen TB
    StaffProfile.objects.create(
        user=jose,
        department=tb_dept,
        category=doc_cat,
        is_active=True
    )
    
    # Berikan izin ke Jose agar bisa akses Dashboard
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType
    
    # Tambahkan izin dasar yang diperlukan
    permissions = Permission.objects.filter(codename__in=[
        'view_menu_medical_records', 'view_patient', 'add_visit', 'change_visit'
    ])
    jose.user_permissions.set(permissions)

    print("--- SETUP SELESAI ---")
    print("User Admin: admin / admin123")
    print("User Jose: jose / jose123")

if __name__ == "__main__":
    full_reset_and_setup()
