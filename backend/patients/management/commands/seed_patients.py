from django.core.management.base import BaseCommand
from patients.models import Patient
import datetime

class Command(BaseCommand):
    help = 'Seeds the database with 3 sample patients'

    def handle(self, *args, **options):
        patients_data = [
            {
                "full_name": "Armindo Dos Santos",
                "date_of_birth": datetime.date(1985, 5, 12),
                "gender": "M",
                "address": "Dili, Comoro",
                "phone_number": "77123456"
            },
            {
                "full_name": "Maria Madalena",
                "date_of_birth": datetime.date(1992, 10, 20),
                "gender": "F",
                "address": "Dili, Bairo Pite",
                "phone_number": "78123456"
            },
            {
                "full_name": "Jose Ramos Horta",
                "date_of_birth": datetime.date(1970, 1, 1),
                "gender": "M",
                "address": "Dili, Farol",
                "phone_number": "75123456"
            }
        ]

        for data in patients_data:
            last_id = Patient.objects.count() + 1
            patient_id = f"MD2026{last_id:04d}"
            
            patient, created = Patient.objects.get_or_create(
                full_name=data['full_name'],
                defaults={
                    'patient_id': patient_id,
                    'date_of_birth': data['date_of_birth'],
                    'gender': data['gender'],
                    'address': data['address'],
                    'phone_number': data['phone_number']
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Successfully created patient: {patient.full_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Patient already exists: {patient.full_name}'))
