from django.db import migrations

def make_patient_visible(apps, schema_editor):
    Patient = apps.get_model('patients', 'Patient')
    # Update Maria to be a normal patient so everyone can see her for the test
    Patient.objects.filter(patient_id='TEST002').update(
        is_lactating=False,
        is_pregnant=False,
        is_hiv_patient=False
    )

class Migration(migrations.Migration):
    dependencies = [
        ('patients', '0020_create_test_patient'),
    ]

    operations = [
        migrations.RunPython(make_patient_visible),
    ]
