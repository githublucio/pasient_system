import qrcode
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from django.core.files.base import ContentFile
from patients.models import Patient
import os

def generate_patient_assets(patient_uuid):
    patient = Patient.objects.get(uuid=patient_uuid)
    
    # 1. Generate QR Code
    # The QR code contains the patient ID (Unit Card Number)
    qr_data = patient.patient_id
    qr = qrcode.QRCode(
        version=1, 
        error_correction=qrcode.constants.ERROR_CORRECT_H, # High error correction for robustness
        box_size=15, # Increased resolution
        border=4
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    
    buffer_qr = BytesIO()
    img_qr.save(buffer_qr, format='PNG')
    patient.qr_code_image.save(f'qr_{patient.patient_id}.png', ContentFile(buffer_qr.getvalue()), save=False)
    
    # 2. Generate Barcode (Code128)
    # The Barcode is used for quick lookup by ID at reception
    code128 = barcode.get_class('code128')
    # High-resolution options for better scanning
    # We remove text from the barcode image itself to ensure bars are maximum clarity
    options = {
        'module_width': 0.3,    # Narrower to prevent text overlap
        'module_height': 18.0,  # Slightly shorter for better vertical fit
        'quiet_zone': 5.0,
        'write_text': False,
        'dpi': 600,
    }
    bar = code128(patient.patient_id, writer=ImageWriter())
    
    buffer_bar = BytesIO()
    bar.write(buffer_bar, options=options)
    patient.barcode_image.save(f'bar_{patient.patient_id}.png', ContentFile(buffer_bar.getvalue()), save=False)
    
    patient.save()
    return True
