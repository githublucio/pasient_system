import os
import django
import sys

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from django.core.management import call_command
from django.contrib.auth.models import User

def run_import():
    print("--- Memulai Proses Import Data Otomatis ---")
    
    # Lokasi file data.json (di root project)
    # Karena script ini di folder 'backend', maka file ada di '../data.json'
    json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data.json'))
    
    if os.path.exists(json_path):
        print(f"File ditemukan di: {json_path}")
        try:
            print("Sedang mengimpor data (ini mungkin memakan waktu)...")
            # Menjalankan loaddata dengan mengabaikan contenttypes dan permissions yang sering bikin error
            call_command('loaddata', json_path, exclude=['contenttypes', 'auth.permission'])
            print("--- Import Berhasil! ---")
        except Exception as e:
            print(f"PERINGATAN: Terjadi kendala saat import: {e}")
            print("Proses dilanjutkan agar server tetap bisa jalan.")
    else:
        print(f"File tidak ditemukan di {json_path}, melewati proses import.")

if __name__ == "__main__":
    run_import()
