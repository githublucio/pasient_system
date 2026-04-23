import os
import sys
import django

# Setup Django Environment
# Add the project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from medical_records.models import Diagnosis

def seed_diagnoses():
    # Helper to add diagnosis and return it
    def add_diag(code, name, parent=None):
        diag, created = Diagnosis.objects.update_or_create(
            code=code,
            defaults={'name': name, 'parent': parent}
        )
        status = "Created" if created else "Updated"
        print(f"{status}: {diag}")
        return diag

    print("--- Seeding Hierarchical Diagnoses (Professional ICD-10) ---")
    
    # 1. Hepatitis Group
    hep = add_diag('B15-B19', 'Hepatitis Viral')
    add_diag('B15', 'Hepatitis A', hep)
    add_diag('B16', 'Hepatitis B', hep)
    add_diag('B17', 'Hepatitis C', hep)
    add_diag('B19', 'Hepatitis Unspecified', hep)

    # 2. Tuberculosis Group
    tb = add_diag('A15-A19', 'Tuberculosis (TB)')
    ptb = add_diag('A15', 'Pulmonary TB (BTA+)', tb)
    add_diag('A16', 'Pulmonary TB (BTA-)', tb)
    etb = add_diag('A18', 'Extra-Pulmonary TB', tb)
    add_diag('A17.0', 'Tuberculous Meningitis', etb)
    add_diag('A18.0', 'TB of Bone and Joints', etb)
    add_diag('A19', 'Miliary Tuberculosis', tb)

    # 3. Diabetes Group
    dm = add_diag('E10-E14', 'Diabetes Mellitus')
    dm1 = add_diag('E10', 'Type 1 Diabetes Mellitus', dm)
    dm2 = add_diag('E11', 'Type 2 Diabetes Mellitus', dm)
    add_diag('E11.9', 'Type 2 DM Without Complications', dm2)
    add_diag('E11.2', 'Type 2 DM With Kidney Complications', dm2)
    add_diag('E11.4', 'Type 2 DM With Neurological Complications', dm2)

    # 4. Dengue Group
    den = add_diag('A90-A91', 'Dengue')
    add_diag('A90', 'Dengue Fever (Classic)', den)
    dhf = add_diag('A91', 'Dengue Hemorrhagic Fever (DHF)', den)
    add_diag('A91.1', 'DHF Grade 1', dhf)
    add_diag('A91.2', 'DHF Grade 2', dhf)
    add_diag('A91.3', 'DHF Grade 3 (DSS)', dhf)
    add_diag('A91.4', 'DHF Grade 4 (DSS)', dhf)

    # 5. Hypertension Group
    ht = add_diag('I10-I15', 'Hypertension')
    add_diag('I10', 'Essential (Primary) Hypertension', ht)
    add_diag('I11', 'Hypertensive Heart Disease', ht)
    add_diag('I12', 'Hypertensive Renal Disease', ht)
    add_diag('I15', 'Secondary Hypertension', ht)

    # 6. Typhoid Group
    typ = add_diag('A01', 'Typhoid and Paratyphoid')
    add_diag('A01.0', 'Typhoid Fever', typ)
    add_diag('A01.1', 'Paratyphoid A', typ)
    add_diag('A01.2', 'Paratyphoid B', typ)

    # 7. Respiratory Infection (ISPA)
    ispa = add_diag('J00-J06', 'ISPA / Acute Upper Respiratory Infections')
    add_diag('J00', 'Nasopharyngitis (Common Cold)', ispa)
    add_diag('J01', 'Acute Sinusitis', ispa)
    add_diag('J02', 'Acute Pharyngitis', ispa)
    add_diag('J03', 'Acute Tonsillitis', ispa)

    # 8. Others from the previous list
    add_diag('B86', 'Scabies')
    add_diag('B01', 'Varisella (Chickenpox)')
    add_diag('R21', 'Fever With Rash')
    add_diag('R17', 'Jaundice Syndrome')
    add_diag('A30', 'Lepra (Hansen\'s Disease)')
    add_diag('H10', 'Konjungtivitis')
    add_diag('B26', 'Mumps (Parotiditis)')
    add_diag('A09', 'Diare and Gastroenteritis')
    add_diag('J18', 'Pneumonia')
    
    # 9. Special Categories
    add_diag('B24', 'B24/VCCT (HIV/AIDS)')
    add_diag('OTHER-SKIN', 'Moras Kulit Seluk')
    add_diag('OTHER', 'Moras Seluk-Seluk (Not In List)')

    print("--- Seeding Complete ---")

if __name__ == "__main__":
    seed_diagnoses()
