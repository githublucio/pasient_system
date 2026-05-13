import os
import django
import json
from uuid import UUID

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from patients.models import Municipio, PostoAdministrativo, Suco, Aldeia, Patient
from medical_records.models import Visit, VitalSigns, Room, Diagnosis, DiagnosisCategory, VisitDiagnosis
from staff.models import Department, StaffCategory, Position, StaffProfile

def run_import():
    print("--- Memulai Proses Import Data Pintar (Legacy Support) ---")
    
    json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data.json'))
    if not os.path.exists(json_path):
        print(f"File {json_path} tidak ditemukan.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Mengolah {len(data)} objek data...")

    # Urutan import untuk menjaga Integritas (Foreign Key)
    # Kita bagi berdasarkan model
    models_data = {
        'auth.group': [],
        'auth.user': [],
        'patients.municipio': [],
        'patients.postoadministrativo': [],
        'patients.suco': [],
        'patients.aldeia': [],
        'staff.department': [],
        'staff.staffcategory': [],
        'staff.position': [],
        'medical_records.room': [],
        'medical_records.diagnosiscategory': [],
        'medical_records.diagnosis': [],
        'patients.patient': [],
        'medical_records.visit': [],
    }

    for item in data:
        model = item['model']
        if model in models_data:
            models_data[model].append(item)

    # 1. Import Master Data Sederhana
    def simple_import(model_class, items):
        count = 0
        for item in items:
            fields = item['fields']
            pk = item.get('pk')
            # Hapus field many-to-many untuk simple create
            m2m = {}
            for field_name, value in list(fields.items()):
                if isinstance(value, list):
                    m2m[field_name] = fields.pop(field_name)
            
            obj, created = model_class.objects.get_or_create(pk=pk, defaults=fields)
            if not created:
                # Update existing
                for k, v in fields.items(): setattr(obj, k, v)
                obj.save()
            
            # Re-add M2M if any
            for field_name, ids in m2m.items():
                if hasattr(obj, field_name):
                    getattr(obj, field_name).set(ids)
            count += 1
        print(f"Imported {count} items for {model_class.__name__}")

    # Jalankan import master data
    simple_import(Group, models_data['auth.group'])
    simple_import(Department, models_data['staff.department'])
    simple_import(StaffCategory, models_data['staff.staffcategory'])
    simple_import(Position, models_data['staff.position'])
    simple_import(Room, models_data['medical_records.room'])
    simple_import(DiagnosisCategory, models_data['medical_records.diagnosiscategory'])
    
    # User
    for item in models_data['auth.user']:
        fields = item['fields']
        groups = fields.pop('groups', [])
        perms = fields.pop('user_permissions', [])
        user, created = User.objects.get_or_create(pk=item['pk'], defaults=fields)
        if not created:
            for k, v in fields.items(): setattr(user, k, v)
            user.save()
        user.groups.set(groups)
        
    # Geografi
    simple_import(Municipio, models_data['patients.municipio'])
    simple_import(PostoAdministrativo, models_data['patients.postoadministrativo'])
    simple_import(Suco, models_data['patients.suco'])
    simple_import(Aldeia, models_data['patients.aldeia'])
    
    # Diagnosis (Recursive FK support)
    simple_import(Diagnosis, models_data['medical_records.diagnosis'])

    # Patient
    simple_import(Patient, models_data['patients.patient'])

    # 2. IMPORT VISIT (DENGAN LOGIKA KONVERSI VITAL SIGNS)
    visit_count = 0
    vital_count = 0
    for item in models_data['medical_records.visit']:
        fields = item['fields']
        pk = item['pk']

        # Daftar field vital signs yang mungkin ada di model lama
        vitals_fields = ['bp_sys', 'bp_dia', 'temp', 'weight', 'spo2', 'pulse', 'rr', 'height_cm', 'muac']
        extracted_vitals = {}
        
        visit_fields = {}
        for k, v in fields.items():
            if k in vitals_fields:
                extracted_vitals[k] = v
            else:
                visit_fields[k] = v

        # Handle ManyToMany like secondary_diagnoses if any
        secondary_diags = visit_fields.pop('secondary_diagnoses', [])
        # Handle diagnosis field (might be a FK in old model)
        legacy_diag_id = visit_fields.pop('diagnosis', None)

        try:
            visit, created = Visit.objects.get_or_create(pk=pk, defaults=visit_fields)
            if not created:
                for k, v in visit_fields.items(): setattr(visit, k, v)
                visit.save()
            
            # Simpan Vital Signs jika ada data
            if extracted_vitals:
                vitals_obj, _ = VitalSigns.objects.get_or_create(visit=visit)
                for k, v in extracted_vitals.items():
                    setattr(vitals_obj, k, v)
                vitals_obj.save()
                vital_count += 1
            
            # Handle legacy diagnosis mapping
            if legacy_diag_id:
                diag = Diagnosis.objects.filter(pk=legacy_diag_id).first()
                if diag:
                    VisitDiagnosis.objects.get_or_create(visit=visit, diagnosis=diag, defaults={'is_primary': True})

            visit_count += 1
        except Exception as e:
            print(f"Gagal mengimpor visit {pk}: {e}")

    print(f"Selesai! Berhasil mengimpor {visit_count} Kunjungan (Visit) dan {vital_count} data Vital Signs.")

if __name__ == "__main__":
    run_import()
