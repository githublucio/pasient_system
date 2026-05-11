from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required, permission_required
from django.utils import timezone

from medical_records.models import Visit
from .models import LabTest, LabRequest, LabResult

CBC_PARAMS = [
    {'key': 'wbc', 'name': 'WBC', 'unit': '10^9/L'},
    {'key': 'rbc', 'name': 'RBC', 'unit': '10^12/L'},
    {'key': 'hgb', 'name': 'HGB', 'unit': 'g/L'},
    {'key': 'hct', 'name': 'HCT', 'unit': 'L/L'},
    {'key': 'mcv', 'name': 'MCV', 'unit': 'fL'},
    {'key': 'mch', 'name': 'MCH', 'unit': 'pg'},
    {'key': 'mchc', 'name': 'MCHC', 'unit': 'g/L'},
    {'key': 'plt', 'name': 'PLT', 'unit': '10^9/L'},
    {'key': 'lymph_pct', 'name': 'Lymph%', 'unit': '%'},
    {'key': 'mid_pct', 'name': 'Mid%', 'unit': '%'},
    {'key': 'gran_pct', 'name': 'Gran%', 'unit': '%'},
    {'key': 'rdw_cv', 'name': 'RDW-CV', 'unit': '%'},
    {'key': 'mpv', 'name': 'MPV', 'unit': 'fL'},
]

CBC_RANGES = {
    'adult_m': {
        'wbc': '4.0 - 10.0', 'rbc': '4.00 - 5.50', 'hgb': '120 - 160', 'hct': '0.400 - 0.540',
        'mcv': '80.0 - 100.0', 'mch': '27.0 - 34.0', 'mchc': '320 - 360',
        'plt': '100 - 300', 'lymph_pct': '20.0 - 40.0', 'mid_pct': '3.0 - 15.0', 'gran_pct': '50.0 - 70.0',
        'rdw_cv': '11.0 - 16.0', 'mpv': '6.5 - 12.0'
    },
    'adult_f': {
        'wbc': '4.0 - 10.0', 'rbc': '3.50 - 5.00', 'hgb': '110 - 150', 'hct': '0.370 - 0.470',
        'mcv': '80.0 - 100.0', 'mch': '27.0 - 34.0', 'mchc': '320 - 360',
        'plt': '100 - 300', 'lymph_pct': '20.0 - 40.0', 'mid_pct': '3.0 - 15.0', 'gran_pct': '50.0 - 70.0',
        'rdw_cv': '11.0 - 16.0', 'mpv': '6.5 - 12.0'
    },
    'child': {
        'wbc': '4.0 - 12.0', 'rbc': '3.50 - 5.20', 'hgb': '120 - 160', 'hct': '0.350 - 0.490',
        'mcv': '80.0 - 100.0', 'mch': '27.0 - 34.0', 'mchc': '310 - 370',
        'plt': '100 - 300', 'lymph_pct': '20.0 - 60.0', 'mid_pct': '3.0 - 15.0', 'gran_pct': '50.0 - 70.0',
        'rdw_cv': '11.0 - 16.0', 'mpv': '6.5 - 12.0'
    },
    'neonate': {
        'wbc': '4.0 - 20.0', 'rbc': '3.50 - 7.00', 'hgb': '170 - 200', 'hct': '0.380 - 0.680',
        'mcv': '95.0 - 125.0', 'mch': '30.0 - 42.0', 'mchc': '300 - 340',
        'plt': '100 - 300', 'lymph_pct': '10.0 - 60.0', 'mid_pct': '3.0 - 15.0', 'gran_pct': '40.0 - 80.0',
        'rdw_cv': '11.0 - 16.0', 'mpv': '-'
    }
}

# --- Comprehensive Lab Parameters ---

SEROLOGY_PARAMS = [
    {'key': 'hbsag', 'name': 'HBsAg', 'unit': '-'},
    {'key': 'hiv', 'name': 'HIV 1&2', 'unit': '-'},
    {'key': 'hpylori', 'name': 'H.pylori', 'unit': '-'},
    {'key': 'malaria', 'name': 'Malaria Ag', 'unit': '-'},
    {'key': 'dengue_ns1', 'name': 'Dengue NS1', 'unit': '-'},
    {'key': 'dengue_ab', 'name': 'Dengue IgG/IgM', 'unit': '-'},
    {'key': 'vdrl', 'name': 'VDRL', 'unit': '-'},
    {'key': 'tpha', 'name': 'TPHA', 'unit': '-'},
    {'key': 'widal', 'name': 'Widal', 'unit': '-'},
    {'key': 'pregnancy', 'name': 'Pregnancy Test (HCG)', 'unit': '-'},
    {'key': 'aborh', 'name': 'ABO & Rh(D)', 'unit': '-'},
]

BIOCHEMISTRY_PARAMS = [
    {'key': 'bun', 'name': 'BUN (Blood Urea Nitrogen)', 'unit': 'mg/dL', 'range': '3.0 - 8.0'},
    {'key': 'creatinine', 'name': 'CRE (Creatinine)', 'unit': 'umol/L', 'range': '45 - 90'},
    {'key': 'ast_sgot', 'name': 'GOT (AST / SGOT)', 'unit': 'U/L', 'range': '14 - 31'},
    {'key': 'alt_sgpt', 'name': 'GPT (ALT / SGPT)', 'unit': 'U/L', 'range': '0 - 35'},
    {'key': 'alp', 'name': 'ALP (Alkaline Phosphatase)', 'unit': 'U/L', 'range': '30 - 110'},
    {'key': 'uric_acid', 'name': 'UA (Uric Acid)', 'unit': 'umol/L', 'range': '210 - 510'},
    {'key': 'cholesterol', 'name': 'TCHO (Total Cholesterol)', 'unit': 'mmol/L', 'range': '0.00 - 5.20'},
    {'key': 'glucose', 'name': 'GLU (Glucose)', 'unit': 'mmol/L', 'range': '3.0 - 5.4'},
    {'key': 'bilirubin_d', 'name': 'DBIL (Bilirubin Direct)', 'unit': 'umol/L', 'range': '0.00 - 17.00'},
]



URINALYSIS_PARAMS = [
    {'key': 'color', 'name': 'Color', 'unit': '-'},
    {'key': 'aspect', 'name': 'Aspect', 'unit': '-'},
    {'key': 'ph', 'name': 'pH', 'unit': '-'},
    {'key': 'sg', 'name': 'S.G.', 'unit': '-'},
    {'key': 'protein', 'name': 'Protein', 'unit': '-'},
    {'key': 'sugar', 'name': 'Sugar', 'unit': '-'},
    {'key': 'ketone', 'name': 'Ketone', 'unit': '-'},
    {'key': 'bilirubin_u', 'name': 'Bilirubin', 'unit': '-'},
    {'key': 'blood', 'name': 'Blood', 'unit': '-'},
    {'key': 'nitrite', 'name': 'Nitrite', 'unit': '-'},
    {'key': 'leucocytes', 'name': 'Leucocytes', 'unit': '-'},
]

MICROSCOPY_PARAMS = [
    {'key': 'epithelial', 'name': 'Epithelial Cells', 'unit': '/hpf'},
    {'key': 'pus_cell', 'name': 'Pus Cells', 'unit': '/hpf'},
    {'key': 'rbc', 'name': 'R.B.C', 'unit': '/hpf'},
    {'key': 'casts', 'name': 'Casts', 'unit': '-'},
    {'key': 'crystals', 'name': 'Crystals', 'unit': '-'},
    {'key': 'yeast', 'name': 'Yeast Cells', 'unit': '-'},
]

MICROBIOLOGY_PARAMS = [
    {'key': 'stool_op', 'name': 'Stool O&P', 'unit': '-'},
    {'key': 'gram_stain', 'name': 'Gram Stain', 'unit': '-'},
    {'key': 'zn_afb', 'name': 'ZN Stain (AFB)', 'unit': '-'},
]

@login_required
@permission_required('laboratory.add_labrequest', raise_exception=True)
def lab_request_create(request, visit_uuid):
    visit = get_object_or_404(Visit, uuid=visit_uuid)
    
    if request.method == 'POST':
        urgency = request.POST.get('urgency', 'NORMAL')
        patient_type = request.POST.get('patient_type', 'OUT')
        special_category = request.POST.get('special_category', '')
        others_note = request.POST.get('others_note', '')
        selected_tests = request.POST.getlist('tests') # List of LabTest IDs
        
        # Determine source from visit
        source_tag = 'IGD' if visit.current_room and visit.current_room.code in ['IGD', 'EMERGENCY'] else 'OPD'

        # Create Lab Request
        lab_request, created = LabRequest.objects.get_or_create(
            visit=visit,
            defaults={
                'requesting_physician': request.user,
                'urgency': urgency,
                'patient_type': patient_type,
                'special_category': special_category,
                'others_note': others_note,
                'source': source_tag,
            }
        )
        
        # If updating existing
        if not created:
            # Update fields if it already existed (e.g. from quick check)
            lab_request.urgency = urgency
            lab_request.patient_type = patient_type
            lab_request.special_category = special_category
            lab_request.others_note = others_note
            lab_request.source = source_tag
            if not lab_request.requesting_physician:
                lab_request.requesting_physician = request.user
            lab_request.save()
            
        # Set tests
        if selected_tests:
            lab_request.tests.set(selected_tests)
        else:
            lab_request.tests.clear()
            
        from medical_records.utils import log_visit_action
        log_visit_action(visit, 'LAB_REQUEST', request.user)
        messages.success(request, _("Laboratory Request Form saved successfully."))
        
        return redirect('perform_examination', visit_uuid=visit.uuid)
        
    # GET context
    tests_c1 = LabTest.objects.filter(column_index=1).order_by('order')
    tests_c2 = LabTest.objects.filter(column_index=2).order_by('order')
    tests_c3 = LabTest.objects.filter(column_index=3).order_by('order')
    
    try:
        existing_request = visit.lab_request
    except LabRequest.DoesNotExist:
        existing_request = None
    
    return render(request, 'laboratory/request_form.html', {
        'visit': visit,
        'tests_c1': tests_c1,
        'tests_c2': tests_c2,
        'tests_c3': tests_c3,
        'existing_request': existing_request,
    })

@login_required
@permission_required('laboratory.change_labrequest', raise_exception=True)
def lab_result_input(request, request_uuid):
    lab_req = get_object_or_404(LabRequest, uuid=request_uuid)
    
    # Check if this is a CBC request or a comprehensive request
    is_cbc_only = lab_req.tests.filter(name__iexact='CBC').exists() and lab_req.tests.count() == 1
    # If it has more than just CBC or doesn't have CBC, we use the comprehensive form
    is_comprehensive = not is_cbc_only
    
    # Precise age calculation
    from medical_records.utils import calculate_precise_age
    age_val, age_cat = calculate_precise_age(lab_req.visit.patient.date_of_birth)
    
    # Determine reference group
    ref_group = age_cat
    if age_cat == 'adult':
        ref_group = 'adult_m' if lab_req.visit.patient.gender == 'M' else 'adult_f'
    
    if request.method == 'POST':
        status = request.POST.get('status', 'PENDING')
        result_text = request.POST.get('result_text', '')
        notes = request.POST.get('notes', '')
        
        try:
            lab_req.status = status
            lab_req.processed_by = request.user
            
            # Save Lab No if provided
            lab_no = request.POST.get('lab_no')
            if lab_no:
                lab_req.lab_no = lab_no
            
            lab_req.save()
        except Exception as e:
            if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
                messages.error(request, _("Error: Lab No already exists. Please use a unique number."))
            else:
                messages.error(request, f"Error: {str(e)}")
            return redirect(request.path)
        
        if status in ['IN_PROGRESS', 'COMPLETED']:
            from .models import LabResult
            result, created = LabResult.objects.get_or_create(
                lab_request=lab_req,
                defaults={'verified_by': request.user}
            )
            result.result_text = result_text
            result.notes = notes
            result.verified_by = request.user
            
            # (Already handled above in the try block for better atomicity)
            
            # Save Structured Data
            if is_cbc_only:
                cbc_data = {}
                raw_data = {}
                for param in CBC_PARAMS:
                    cbc_data[param['key']] = request.POST.get(f'result_{param["key"]}', '')
                    raw_data[param['key']] = request.POST.get(f'raw_{param["key"]}', '')
                
                result.result_data = {
                    'cbc': cbc_data,
                    'raw': raw_data,
                    'category': ref_group
                }
            else:
                # Comprehensive saving
                data = {
                    'serology': {p['key']: request.POST.get(f's_{p["key"]}', '') for p in SEROLOGY_PARAMS},
                    'biochemistry': {
                        p['key']: {
                            'value': request.POST.get(f'b_{p["key"]}', ''),
                            'remark': request.POST.get(f'br_{p["key"]}', '')
                        } for p in BIOCHEMISTRY_PARAMS
                    },
                    'urinalysis': {p['key']: request.POST.get(f'u_{p["key"]}', '') for p in URINALYSIS_PARAMS},
                    'microscopy': {p['key']: request.POST.get(f'ms_{p["key"]}', '') for p in MICROSCOPY_PARAMS},
                    'microbiology': {p['key']: request.POST.get(f'm_{p["key"]}', '') for p in MICROBIOLOGY_PARAMS},
                }

                
                # Also save CBC if present in comprehensive
                if lab_req.tests.filter(name__iexact='CBC').exists():
                    cbc_data = {param['key']: request.POST.get(f'result_{param["key"]}', '') for param in CBC_PARAMS}
                    raw_data = {param['key']: request.POST.get(f'raw_{param["key"]}', '') for param in CBC_PARAMS}
                    data['cbc'] = cbc_data
                    data['raw'] = raw_data
                    data['category'] = ref_group
                
                result.result_data = data
            
            if 'attachment' in request.FILES:
                result.attachment = request.FILES['attachment']
            
            if status == 'COMPLETED':
                result.completed_at = timezone.now()
            
            result.save()
            
            from .models import LabResultAttachment
            for f in request.FILES.getlist('attachments'):
                LabResultAttachment.objects.create(lab_result=result, file=f)
        
        from medical_records.utils import log_visit_action
        log_visit_action(lab_req.visit, 'LAB_RESULT', request.user)
        messages.success(request, _("Lab result updated successfully."))
        return redirect('lab_dashboard')
    
    from django.core.exceptions import ObjectDoesNotExist
    try:
        existing_result = lab_req.result
    except ObjectDoesNotExist:
        existing_result = None
    
    # Get last lab number for placeholder
    from django.db.models import Max
    last_req = LabRequest.objects.exclude(lab_no__isnull=True).exclude(lab_no='').order_by('-date_of_request').first()
    last_lab_no = last_req.lab_no if last_req else "None"
    
    if is_cbc_only:
        # Prepare parameters with ranges for the template
        params_with_ranges = []
        ranges = CBC_RANGES.get(ref_group, CBC_RANGES['adult_m'])
        for p in CBC_PARAMS:
            params_with_ranges.append({
                'key': p['key'],
                'name': p['name'],
                'unit': p['unit'],
                'range': ranges.get(p['key'], '-')
            })
        
        age_display = f"{age_val} {age_cat}"
        
        existing_results = existing_result.result_data.get('cbc', {}) if existing_result and existing_result.result_data else {}
        existing_raw = existing_result.result_data.get('raw', {}) if existing_result and existing_result.result_data else {}
        
        return render(request, 'laboratory/cbc_result_form.html', {
            'lab_request': lab_req,
            'existing_result': existing_result,
            'cbc_parameters': params_with_ranges,
            'age_category': ref_group,
            'age_display': age_display,
            'existing_raw': existing_raw,
            'last_lab_no': last_lab_no,
        })
    
    # COMPREHENSIVE FORM
    res_data = existing_result.result_data if existing_result else {}
    
    # Prepare CBC context if needed for comprehensive
    has_cbc = lab_req.tests.filter(name__iexact='CBC').exists()
    cbc_params_with_ranges = []
    if has_cbc:
        ranges = CBC_RANGES.get(ref_group, CBC_RANGES['adult_m'])
        for p in CBC_PARAMS:
            cbc_params_with_ranges.append({
                'key': p['key'],
                'name': p['name'],
                'unit': p['unit'],
                'range': ranges.get(p['key'], '-')
            })
    
    # Determine active columns for comprehensive display
    active_columns = set(lab_req.tests.values_list('column_index', flat=True))

    return render(request, 'laboratory/lab_result_form_comprehensive.html', {
        'lab_request': lab_req,
        'existing_result': existing_result,
        'serology_params': SEROLOGY_PARAMS,
        'biochemistry_params': BIOCHEMISTRY_PARAMS,
        'urinalysis_params': URINALYSIS_PARAMS,
        'microscopy_params': MICROSCOPY_PARAMS,
        'microbiology_params': MICROBIOLOGY_PARAMS,
        'cbc_params': cbc_params_with_ranges,
        'has_cbc': has_cbc,
        'age_category': ref_group,
        'age_display': f"{age_val} {age_cat}",
        'existing_serology': res_data.get('serology', {}),
        'existing_biochem': res_data.get('biochemistry', {}),
        'existing_urinalysis': res_data.get('urinalysis', {}),
        'existing_microscopy': res_data.get('microscopy', {}),
        'existing_micro': res_data.get('microbiology', {}),
        'existing_cbc': res_data.get('cbc', {}),
        'existing_cbc_raw': res_data.get('raw', {}),
        'active_columns': active_columns,
        'last_lab_no': last_lab_no,
    })



@login_required
@permission_required('laboratory.view_labrequest', raise_exception=True)
def lab_patient_list(request):
    """Daftar semua pasien yang punya lab request (dari OPD/IGD). Khusus lab staff."""
    from django.db.models import Q, Exists, OuterRef
    from django.core.paginator import Paginator

    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    source_filter = request.GET.get('source', '')
    date_filter = request.GET.get('date', '')

    qs = LabRequest.objects.select_related(
        'visit__patient', 'requesting_physician', 'processed_by'
    ).prefetch_related('tests').order_by('-date_of_request')

    # Annotate whether a LabResult exists
    qs = qs.annotate(
        result_exists=Exists(
            LabResult.objects.filter(lab_request=OuterRef('pk'))
        )
    )

    if query:
        qs = qs.filter(
            Q(visit__patient__full_name__icontains=query) |
            Q(visit__patient__patient_id__icontains=query) |
            Q(lab_no__icontains=query)
        )

    if status_filter:
        qs = qs.filter(status=status_filter)

    if source_filter:
        qs = qs.filter(source=source_filter)

    if date_filter:
        try:
            from datetime import datetime
            fd = datetime.strptime(date_filter, '%Y-%m-%d').date()
            qs = qs.filter(date_of_request__date=fd)
        except ValueError:
            pass

    # Stats (before pagination)
    stats = {
        'pending': qs.filter(status='PENDING').count(),
        'in_progress': qs.filter(status__in=['SAMPLE_COLLECTED', 'IN_PROGRESS']).count(),
        'completed': qs.filter(status='COMPLETED').count(),
        'total': qs.count(),
    }

    paginator = Paginator(qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'laboratory/patient_list.html', {
        'lab_requests': page_obj,
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
        'source_filter': source_filter,
        'date_filter': date_filter,
        'stats': stats,
    })


@login_required
def lab_dashboard(request):
    date_str = request.GET.get('date', '')
    if date_str:
        try:
            from datetime import datetime
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            filter_date = timezone.localdate()
    else:
        filter_date = timezone.localdate()

    from django.db.models import Q
    all_requests = LabRequest.objects.select_related('visit__patient', 'requesting_physician').prefetch_related('tests').order_by('-date_of_request')

    # New requests for the selected date, excluding finished ones (COMPLETED/CANCELLED)
    new_requests = all_requests.filter(
        date_of_request__date=filter_date
    ).exclude(status__in=['COMPLETED', 'CANCELLED'])

    # Continued requests (pending from previous days), strictly excluding finished ones
    continued_requests = all_requests.filter(
        date_of_request__date__lt=filter_date
    ).exclude(status__in=['COMPLETED', 'CANCELLED'])

    # Completed requests strictly based on when the RESULT was finished (today/filtered date)
    completed_today = all_requests.filter(
        status='COMPLETED',
        result__completed_at__date=filter_date
    )

    stats = {
        'pending': all_requests.exclude(status__in=['COMPLETED', 'CANCELLED']).count(),
        'completed': completed_today.count(),
        'total': all_requests.filter(date_of_request__date=filter_date).count(),
    }

    return render(request, 'laboratory/dashboard.html', {
        'new_requests': new_requests,
        'continued_requests': continued_requests,
        'completed_requests': completed_today,
        'filter_date': filter_date,
        'stats': stats,
    })

@login_required
@permission_required('laboratory.change_labrequest', raise_exception=True)
def lab_request_cancel(request, request_uuid):
    lab_req = get_object_or_404(LabRequest, uuid=request_uuid)
    if request.method == 'POST':
        reason = request.POST.get('cancel_reason', '')
        lab_req.status = 'CANCELLED'
        lab_req.cancel_reason = reason
        lab_req.cancelled_by = request.user
        lab_req.save()
        
        from medical_records.utils import log_visit_action
        log_visit_action(lab_req.visit, 'LAB_CANCELLED', request.user)
        
        messages.warning(request, _('Laboratory request has been cancelled.'))
        return redirect('lab_dashboard')
    
    return render(request, 'laboratory/confirm_cancel.html', {'lab_req': lab_req})
