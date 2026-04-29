from django.db import migrations
import datetime

def create_test_patient(apps, schema_editor):
    Patient = apps.get_model('patients', 'Patient')
    
    # Check if TEST002 already exists to avoid duplicates
    if not Patient.objects.filter(patient_id='TEST002').exists():
        Patient.objects.create(
            patient_id='TEST002',
            full_name='Maria Menyusui',
            date_of_birth=datetime.date(1995, 5, 20),
            gender='F',
            registration_fee=0.00,
            is_lactating=True,
            address='Dili, Timor-Leste'
        )

def remove_test_patient(apps, schema_editor):
    Patient = apps.get_model('patients', 'Patient')
    Patient.objects.filter(patient_id='TEST002').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('patients', '0019_patient_idx_patient_id_trgm'),
    ]

    operations = [
        migrations.RunPython(create_test_patient, reverse_code=remove_test_patient),
    ]
