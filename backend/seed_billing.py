#!/usr/bin/env python
"""Seed billing service categories and prices."""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')

sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from billing.models import ServiceCategory, ServicePrice

CATEGORIES = [
    {
        'name': 'Radiology / X-Ray',
        'code': 'RADIOLOGY',
        'icon': 'bi-heart-pulse',
        'order': 1,
        'services': [
            ('X-Ray Chest (PA)', 'XR-CHEST', 5.00),
            ('X-Ray Extremity', 'XR-EXTREM', 5.00),
            ('X-Ray Abdomen', 'XR-ABDO', 5.00),
            ('X-Ray Spine', 'XR-SPINE', 7.00),
            ('X-Ray Skull', 'XR-SKULL', 5.00),
        ]
    },
    {
        'name': 'USG (Ultrasound)',
        'code': 'USG',
        'icon': 'bi-broadcast',
        'order': 2,
        'services': [
            ('USG Abdomen', 'USG-ABDO', 10.00),
            ('USG Obstetric', 'USG-OBS', 10.00),
            ('USG Pelvic', 'USG-PEL', 10.00),
            ('USG Thyroid', 'USG-THY', 10.00),
        ]
    },
    {
        'name': 'Laboratory - Blood Test',
        'code': 'LAB_BLOOD',
        'icon': 'bi-droplet-half',
        'order': 3,
        'services': [
            ('Complete Blood Count (CBC)', 'LAB-CBC', 3.00),
            ('Blood Glucose (Fasting)', 'LAB-GLU-F', 2.00),
            ('Blood Glucose (Random)', 'LAB-GLU-R', 2.00),
            ('Liver Function Test', 'LAB-LFT', 5.00),
            ('Renal Function Test', 'LAB-RFT', 5.00),
            ('Blood Type (ABO/Rh)', 'LAB-BT', 3.00),
            ('Malaria RDT', 'LAB-MAL', 2.00),
            ('HIV Rapid Test', 'LAB-HIV', 0.00),
            ('Dengue NS1', 'LAB-DEN', 3.00),
            ('HbA1c', 'LAB-HBA1C', 5.00),
        ]
    },
    {
        'name': 'Laboratory - Urine Test',
        'code': 'LAB_URINE',
        'icon': 'bi-eyedropper',
        'order': 4,
        'services': [
            ('Urinalysis (Dipstick)', 'LAB-UA', 2.00),
            ('Urine Pregnancy Test', 'LAB-UPT', 1.00),
            ('Urine Culture', 'LAB-UC', 5.00),
        ]
    },
    {
        'name': 'Pathology',
        'code': 'PATHOLOGY',
        'icon': 'bi-microscope',
        'order': 5,
        'services': [
            ('Pap Smear', 'PATH-PAP', 5.00),
            ('Biopsy', 'PATH-BIO', 10.00),
            ('Sputum AFB', 'PATH-AFB', 2.00),
        ]
    },
    {
        'name': 'Consultation',
        'code': 'CONSULT',
        'icon': 'bi-person-badge',
        'order': 6,
        'services': [
            ('General Consultation', 'CON-GEN', 1.00),
            ('Specialist Consultation', 'CON-SPEC', 3.00),
            ('Follow-up Visit', 'CON-FU', 0.50),
        ]
    },
    {
        'name': 'Procedure / Treatment',
        'code': 'PROCEDURE',
        'icon': 'bi-bandaid',
        'order': 7,
        'services': [
            ('Wound Dressing', 'PRO-WD', 2.00),
            ('Minor Surgery', 'PRO-MS', 10.00),
            ('Injection / IV', 'PRO-INJ', 1.00),
            ('Nebulizer', 'PRO-NEB', 2.00),
        ]
    },
    {
        'name': 'Other Services',
        'code': 'OTHER',
        'icon': 'bi-tag',
        'order': 99,
        'services': [
            ('Medical Certificate', 'OTH-MC', 2.00),
            ('Referral Letter', 'OTH-REF', 1.00),
        ]
    },
]

created_cats = 0
created_svcs = 0

for cat_data in CATEGORIES:
    cat, cat_created = ServiceCategory.objects.get_or_create(
        code=cat_data['code'],
        defaults={
            'name': cat_data['name'],
            'icon': cat_data['icon'],
            'order': cat_data['order'],
        }
    )
    if cat_created:
        created_cats += 1
        print(f"  + Category: {cat.name}")

    for svc_name, svc_code, svc_price in cat_data['services']:
        svc, svc_created = ServicePrice.objects.get_or_create(
            code=svc_code,
            defaults={
                'category': cat,
                'name': svc_name,
                'price': svc_price,
            }
        )
        if svc_created:
            created_svcs += 1
            print(f"    + Service: {svc_name} (${svc_price})")

print(f"\nDone! Created {created_cats} categories, {created_svcs} services.")
