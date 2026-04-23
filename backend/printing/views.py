from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from patients.models import Patient
from .utils import generate_patient_assets
from django.http import HttpResponse

@login_required
def preview_card(request, uuid):
    patient = get_object_or_404(Patient, uuid=uuid)
    
    # Ensure QR/Barcode are generated
    if not patient.qr_code_image or not patient.barcode_image:
        generate_patient_assets(patient.uuid)
        patient.refresh_from_db()
        
    return render(request, 'printing/card_preview.html', {
        'patient': patient,
        'logo_url': '/media/Logo.png',
        'front_bg_url': '/media/carad_bacgroun.jpeg',
        'back_bg_url': '/media/carad_bacgroun.jpeg',
    })

@login_required
def print_card_trigger(request, uuid):
    # This endpoint will eventually send a signal to the Local Print Agent
    return HttpResponse("Signal sent to Printer")
