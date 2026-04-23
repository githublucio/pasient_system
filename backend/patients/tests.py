from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from .models import Municipio, PostoAdministrativo, Suco, Aldeia, Patient
import datetime

class MasterDataProtectionTest(TestCase):
    def setUp(self):
        self.municipio = Municipio.objects.create(name="Bobonaro")
        self.posto = PostoAdministrativo.objects.create(municipio=self.municipio, name="Maliana")
        self.suco = Suco.objects.create(posto=self.posto, name="Holsa")
        self.aldeia = Aldeia.objects.create(suco=self.suco, name="Odomau")

    def test_delete_municipio_with_posto_fails(self):
        """Deleting a Municipio that has a Posto should raise ProtectedError."""
        with self.assertRaises(ProtectedError):
            self.municipio.delete()

    def test_delete_posto_with_suco_fails(self):
        """Deleting a Posto that has a Suco should raise ProtectedError."""
        with self.assertRaises(ProtectedError):
            self.posto.delete()

    def test_delete_suco_with_aldeia_fails(self):
        """Deleting a Suco that has an Aldeia should raise ProtectedError."""
        with self.assertRaises(ProtectedError):
            self.suco.delete()

    def test_delete_aldeia_with_patient_fails(self):
        """Deleting an Aldeia that has a Patient should raise ProtectedError."""
        Patient.objects.create(
            patient_id="P001",
            full_name="John Doe",
            date_of_birth="1990-01-01",
            gender="M",
            aldeia=self.aldeia
        )
        with self.assertRaises(ProtectedError):
            self.aldeia.delete()

    def test_reparenting_posto_with_children_fails(self):
        """Changing the Municipio of a Posto that has Sucos should raise ValidationError."""
        new_muni = Municipio.objects.create(name="Dili")
        self.posto.municipio = new_muni
        with self.assertRaises(ValidationError):
            self.posto.clean()

    def test_reparenting_suco_with_children_fails(self):
        """Changing the Posto of a Suco that has Aldeias should raise ValidationError."""
        new_muni = Municipio.objects.create(name="Dili")
        new_posto = PostoAdministrativo.objects.create(municipio=new_muni, name="Vera Cruz")
        self.suco.posto = new_posto
        with self.assertRaises(ValidationError):
            self.suco.clean()

    def test_delete_empty_aldeia_succeeds(self):
        """Deleting an Aldeia with no patients should succeed."""
        empty_aldeia = Aldeia.objects.create(suco=self.suco, name="Empty")
        empty_aldeia.delete()
        self.assertFalse(Aldeia.objects.filter(name="Empty").exists())


class PatientModelTest(TestCase):
    def test_patient_creation_with_blood_type(self):
        patient = Patient.objects.create(
            patient_id='MD20260099', full_name='Blood Test',
            date_of_birth=datetime.date(1990, 1, 1), gender='M',
            blood_type='O+'
        )
        self.assertEqual(patient.blood_type, 'O+')

    def test_patient_age_calculation(self):
        import datetime as dt
        patient = Patient.objects.create(
            patient_id='MD20260098', full_name='Age Test',
            date_of_birth=dt.date(2000, 1, 1), gender='F'
        )
        self.assertGreater(patient.age, 0)

    def test_patient_full_address(self):
        muni = Municipio.objects.create(name='Test Muni')
        patient = Patient.objects.create(
            patient_id='MD20260097', full_name='Addr Test',
            date_of_birth=datetime.date(1990, 1, 1), gender='M',
            municipio=muni
        )
        self.assertIn('Test Muni', patient.full_address)


class PatientFormValidationTest(TestCase):
    def test_future_dob_rejected(self):
        from patients.forms import PatientRegistrationForm
        import datetime as dt
        form = PatientRegistrationForm(data={
            'full_name': 'Future Baby',
            'date_of_birth': (dt.date.today() + dt.timedelta(days=30)).isoformat(),
            'gender': 'M',
            'patient_category': 'RAI_LARAN',
            'registration_fee': '0.00',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('date_of_birth', form.errors)
