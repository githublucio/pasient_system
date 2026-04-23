import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from laboratory.models import LabTest

# Column 1
tests_c1 = [
    'Hb', 'Malaria', 'Dengue', 'HIV', 'B.S', 'HCG', 'Urine Dip', 'ABO&Rh(D)'
]

# Column 2
tests_c2 = [
    'Hep. B', 'Hep.C', 'RPR/VDRL', 'G.O. Smear', 'Prenatal Panel', 'Urine Sediment', 'Smear Morphology'
]

# Column 3
tests_c3 = [
    'CBC', 'U&E', 'LFT', 'INR', 'Shyphilis(R', 'Gonorrhea', 'Stool O&P', 'Gram Stall'
]

def seed():
    LabTest.objects.all().delete()
    
    order = 1
    for name in tests_c1:
        LabTest.objects.create(name=name, column_index=1, order=order)
        order += 1
        
    order = 1
    for name in tests_c2:
        LabTest.objects.create(name=name, column_index=2, order=order)
        order += 1
        
    order = 1
    for name in tests_c3:
        LabTest.objects.create(name=name, column_index=3, order=order)
        order += 1
        
    print("LabTests seeded successfully based on Bairo Pite form.")

if __name__ == '__main__':
    seed()
