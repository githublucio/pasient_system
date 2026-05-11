import os
import django
from django.apps import apps

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

mermaid_code = 'erDiagram\n'

for model in apps.get_models():
    model_name = model.__name__
    if model._meta.app_label in ['auth', 'contenttypes', 'sessions', 'admin', 'messages', 'staticfiles']:
        continue
    mermaid_code += f'    {model_name} {{\n'
    for field in model._meta.fields:
        field_type = field.get_internal_type().replace('Field', '')
        field_name = field.name
        mermaid_code += f'        {field_type} {field_name}\n'
    mermaid_code += '    }\n'
    
    for field in model._meta.get_fields():
        if field.is_relation and (field.many_to_one or field.many_to_many or field.one_to_one):
            if hasattr(field, 'remote_field') and field.remote_field:
                related_model = field.related_model
                if related_model and related_model._meta.app_label not in ['auth', 'contenttypes', 'sessions', 'admin', 'messages', 'staticfiles']:
                    related_name = related_model.__name__
                    rel_type = ''
                    if field.many_to_one:
                        rel_type = '}o--||'
                    elif field.many_to_many:
                        rel_type = '}o--o{'
                    elif field.one_to_one:
                        rel_type = '||--||'
                    if rel_type:
                        mermaid_code += f'    {model_name} {rel_type} {related_name} : "{field.name}"\n'

html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Database ERD - Resolusi Tinggi</title>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{ 
          startOnLoad: true, 
          theme: 'default',
          securityLevel: 'loose',
          maxTextSize: 9000000,
          er: {{
              useMaxWidth: false
          }}
      }});
    </script>
    <style>
        body {{ font-family: sans-serif; margin: 20px; }}
        .mermaid {{ width: 100%; overflow: auto; }}
        .controls {{ margin-bottom: 20px; padding: 10px; background: #f0f0f0; border-radius: 5px; }}
        button {{ padding: 8px 16px; margin-right: 10px; cursor: pointer; }}
    </style>
</head>
<body>
    <div class="controls">
        <h2>Database Entity Relationship Diagram (ERD)</h2>
        <p>ERD Resolusi Tinggi (Mermaid.js). Anda dapat membaca dengan jelas karena ini adalah gambar vektor (bukan raster).</p>
        <p><strong>Cara Download:</strong></p>
        <ul>
            <li><strong>PDF:</strong> Tekan tombol Print / Cetak di bawah ini, lalu pilih tujuan (Destination) "Save as PDF" / "Simpan sebagai PDF".</li>
            <li><strong>SVG / PNG:</strong> Klik kanan pada diagram di bawah ini lalu pilih "Save image as..." (tergantung browser).</li>
        </ul>
        <button onclick="window.print()">Print / Save as PDF</button>
    </div>
    <div class="mermaid">
{mermaid_code}
    </div>
</body>
</html>'''

with open('ERD_Database.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print('Created ERD_Database.html')
