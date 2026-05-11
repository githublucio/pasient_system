import os
import django
from django.apps import apps

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

modules = {
    'MasterWilayah': ['Municipio', 'PostoAdministrativo', 'Suco', 'Aldeia'],
    'PatientManagement': ['Patient', 'PatientID', 'PatientAllergy'],
    'VisitAndRegistration': ['Visit', 'VitalSigns', 'VisitDiagnosis', 'VisitLog', 'EmergencyObservation', 'EmergencyMedication', 'HIVAssessment', 'TBScreening', 'Appointment', 'DailyQueue'],
    'BillingFinance': ['Invoice', 'InvoiceItem', 'Payment', 'ServiceCategory', 'ServicePrice'],
    'Pharmacy': ['Medicine', 'StockBatch', 'Prescription', 'PrescriptionItem', 'DispensedItem'],
    'Laboratory': ['LabTest', 'LabRequest', 'LabResult', 'LabResultAttachment'],
    'Radiology': ['RadiologyTest', 'RadiologyRequest', 'RadiologyResult', 'RadiologyResultAttachment'],
    'Pathology': ['PathologyTest', 'PathologyRequest', 'PathologyResult', 'PathologyResultAttachment'],
    'StaffHR': ['Department', 'Position', 'StaffCategory', 'StaffProfile', 'AuditLog'],
    'Reference': ['Room', 'Diagnosis', 'DiagnosisCategory'],
}

mermaid_code = 'classDiagram\n'

# Track processed models to avoid duplicates and handle unassigned ones
processed_models = set()

for module_name, models_in_module in modules.items():
    mermaid_code += f'    namespace {module_name} {{\n'
    for model_name in models_in_module:
        try:
            model = next(m for m in apps.get_models() if m.__name__ == model_name)
            processed_models.add(model_name)
            mermaid_code += f'        class {model_name} {{\n'
            for field in model._meta.fields:
                field_type = field.get_internal_type().replace('Field', '')
                field_name = field.name
                mermaid_code += f'            +{field_type} {field_name}\n'
            mermaid_code += '        }\n'
        except StopIteration:
            pass
    mermaid_code += '    }\n'

# Relationships
for model in apps.get_models():
    model_name = model.__name__
    if model._meta.app_label in ['auth', 'contenttypes', 'sessions', 'admin', 'messages', 'staticfiles']:
        continue
    
    for field in model._meta.get_fields():
        if field.is_relation and (field.many_to_one or field.many_to_many or field.one_to_one):
            if hasattr(field, 'remote_field') and field.remote_field:
                related_model = field.related_model
                if related_model and related_model._meta.app_label not in ['auth', 'contenttypes', 'sessions', 'admin', 'messages', 'staticfiles']:
                    related_name = related_model.__name__
                    rel_type = ''
                    if field.many_to_one:
                        rel_type = '--> '
                    elif field.many_to_many:
                        rel_type = '<--> '
                    elif field.one_to_one:
                        rel_type = '-- '
                    if rel_type:
                        mermaid_code += f'    {model_name} {rel_type} {related_name} : {field.name}\n'

html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Database ERD - Class Diagram</title>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{ 
          startOnLoad: true, 
          theme: 'default',
          securityLevel: 'loose',
          maxTextSize: 9000000
      }});
    </script>
    <style>
        body {{ font-family: sans-serif; margin: 20px; background: #f9f9f9; }}
        .mermaid {{ width: 100%; overflow: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .controls {{ margin-bottom: 20px; padding: 15px; background: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 5px solid #0d6efd; }}
        button {{ padding: 10px 20px; margin-right: 10px; cursor: pointer; background: #0d6efd; color: white; border: none; border-radius: 4px; font-weight: bold; }}
        button:hover {{ background: #0b5ed7; }}
    </style>
</head>
<body>
    <div class="controls">
        <h2>ERD Visual (Mirip Gambar Anda)</h2>
        <p>Saya telah mengelompokkan tabel ke dalam kotak-kotak modul (Namespace) seperti gambar yang Anda kirimkan. Karena ini adalah render vektor, kualitasnya sangat tinggi.</p>
        <p><strong>Cara Menyimpan sebagai Gambar (PNG/JPG):</strong></p>
        <ol>
            <li>Gunakan ekstensi browser seperti "GoFullPage" atau "FireShot" untuk mengambil screenshot satu halaman penuh.</li>
            <li>ATAU klik tombol di bawah ini untuk mencetaknya sebagai PDF berkualitas tinggi.</li>
        </ol>
        <button onclick="window.print()"><svg style="width:16px;height:16px;vertical-align:middle;margin-right:5px" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"></path></svg> Cetak / Simpan ke PDF</button>
    </div>
    <div class="mermaid">
{mermaid_code}
    </div>
</body>
</html>'''

with open('ERD_Visual_Berwarna.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print('Created ERD_Visual_Berwarna.html')
