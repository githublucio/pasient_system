import os
import django
from django.db import connection

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

def reset_sequences():
    print("--- Menyelaraskan Urutan ID Database (Reset Sequences) ---")
    
    # Perintah Django untuk menghasilkan SQL reset sequence
    from django.core.management import call_command
    from io import StringIO

    # Daftar aplikasi yang perlu di-reset
    apps = ['auth', 'patients', 'medical_records', 'staff', 'pharmacy', 'laboratory', 'billing', 'radiology', 'pathology']
    
    for app in apps:
        output = StringIO()
        try:
            call_command('sqlsequencereset', app, stdout=output, no_color=True)
            sql = output.getvalue()
            if sql:
                with connection.cursor() as cursor:
                    cursor.execute(sql)
                print(f"Resetted sequences for app: {app}")
        except Exception as e:
            print(f"Gagal reset sequence untuk {app}: {e}")

    print("--- Sinkronisasi Selesai ---")

if __name__ == "__main__":
    reset_sequences()
