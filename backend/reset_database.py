import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from django.contrib.auth.models import User
from patients.models import Patient, PatientID, DailyQueue
from medical_records.models import Visit, TBCase, HIVAssessment, Diagnosis
from staff.models import StaffProfile
from appointments.models import Appointment
from billing.models import Invoice, Payment
from pharmacy.models import MedicineInventory, Prescription
from laboratory.models import LabRequest
from django.db import connection

def reset_data():
    print("--- Memulai Pembersihan Database (FULL RESET) ---")
    
    try:
        # Hapus data transaksi dengan urutan yang benar (menghindari constraint error)
        print("Menghapus data transaksi (Visits, Billing, Pharmacy, Lab)...")
        Payment.objects.all().delete()
        Invoice.objects.all().delete()
        Prescription.objects.all().delete()
        LabRequest.objects.all().delete()
        Appointment.objects.all().delete()
        TBCase.objects.all().delete()
        HIVAssessment.objects.all().delete()
        Visit.objects.all().delete()
        
        # Hapus data pasien
        print("Menghapus data pasien...")
        PatientID.objects.all().delete()
        Patient.objects.all().delete()
        DailyQueue.objects.all().delete()
        
        # Hapus data staff dan user
        print("Menghapus data user dan staff...")
        StaffProfile.objects.all().delete()
        User.objects.all().delete()
        
        print("--- DATABASE BERSIH TOTAL ---")
    except Exception as e:
        print(f"Error saat membersihkan data: {str(e)}")

if __name__ == "__main__":
    reset_data()
