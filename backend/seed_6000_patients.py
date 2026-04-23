import os
import django
import random
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from patients.models import Patient, Aldeia

def seed_patients(count=6000):
    print(f"--- Seeding {count} Patients ---")
    
    first_names_m = ["Joao", "Jose", "Antonio", "Domingos", "Augusto", "Francisco", "Manuel", "Mateus", "Miguel", "Pedro"]
    first_names_f = ["Maria", "Filomena", "Lucia", "Rosa", "Teresa", "Isabel", "Ana", "Jacinta", "Lourdes", "Beatriz"]
    last_names = ["Soares", "Pinto", "da Costa", "Amaral", "Belo", "Martins", "Guterres", "Pereira", "Ximenes", "da Silva", "Lopes", "Fernandes", "Gomes", "Alves", "Cardoso"]
    
    aldeias = list(Aldeia.objects.select_related('suco__posto__municipio').all())
    if not aldeias:
        print("No geography data (Aldeia) found. Please seed geography first.")
        return

    existing_count = Patient.objects.count()
    start_id = existing_count + 100
    
    patients_to_create = []
    
    for i in range(count):
        gender = random.choice(['M', 'F'])
        first_name = random.choice(first_names_m if gender == 'M' else first_names_f)
        last_name = random.choice(last_names)
        full_name = f"{first_name} {last_name} {random.choice(last_names)}"
        
        dob = date(1950, 1, 1) + timedelta(days=random.randint(0, 365*70))
        p_id = f"MD2026{start_id + i:05d}"
        
        aldeia = random.choice(aldeias)
        suco = aldeia.suco
        posto = suco.posto
        muni = posto.municipio
        
        patient = Patient(
            patient_id=p_id,
            full_name=full_name.lower(),
            date_of_birth=dob,
            gender=gender,
            municipio=muni,
            posto_administrativo=posto,
            suco=suco,
            aldeia=aldeia,
            phone_number=f"77{random.randint(1000000, 9999999)}",
            registration_fee=2.00
        )
        patients_to_create.append(patient)
        
        if len(patients_to_create) >= 1000:
            Patient.objects.bulk_create(patients_to_create)
            print(f"Inserted {i+1} patients...")
            patients_to_create = []
            
    if patients_to_create:
        Patient.objects.bulk_create(patients_to_create)
        
    print(f"--- Successfully seeded {count} patients! ---")

if __name__ == "__main__":
    seed_patients(6000)
