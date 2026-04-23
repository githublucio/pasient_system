from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from medical_records.models import Visit
from .models import PathologyRequest, PathologyTest

@login_required
@permission_required('pathology.add_pathologyrequest', raise_exception=True)
def pathology_request_create(request, visit_uuid):
    visit = get_object_or_404(Visit, uuid=visit_uuid)
    
    if request.method == 'POST':
        is_emergency = visit.current_room and visit.current_room.code in ['IGD', 'EMERGENCY']
        patho_req, created = PathologyRequest.objects.get_or_create(
            visit=visit,
            defaults={
                'requesting_physician': request.user,
                'source': 'IGD' if is_emergency else 'OPD'
            }
        )
        
        # Update scalar fields
        patho_req.fasting = request.POST.get('fasting') == 'True'
        patho_req.clinica_history = request.POST.get('clinica_history', '')
        patho_req.billing_type = request.POST.get('billing_type', 'O')
        
        patho_req.tube_sst = request.POST.get('tube_sst', '')
        patho_req.tube_edta = request.POST.get('tube_edta', '')
        patho_req.tube_esr = request.POST.get('tube_esr', '')
        patho_req.tube_plain = request.POST.get('tube_plain', '')
        patho_req.tube_cit = request.POST.get('tube_cit', '')
        patho_req.tube_flok = request.POST.get('tube_flok', '')
        patho_req.tube_msu = request.POST.get('tube_msu', '')
        patho_req.tube_swabs = request.POST.get('tube_swabs', '')
        patho_req.tube_pap = request.POST.get('tube_pap', '')
        patho_req.tube_other = request.POST.get('tube_other', '')
        
        patho_req.requesting_physician = request.user
        patho_req.save()
        
        # Update M2M field
        selected_test_ids = request.POST.getlist('tests')
        if selected_test_ids:
            tests = PathologyTest.objects.filter(id__in=selected_test_ids)
            patho_req.tests.set(tests)
        else:
            patho_req.tests.clear()
        
        from medical_records.utils import log_visit_action
        log_visit_action(visit, 'PATHO_REQUEST', request.user)
        messages.success(request, _("Pathology Form saved successfully."))
        return redirect('perform_examination', visit_uuid=visit.uuid)
        
    try:
        existing_request = visit.pathology_request
    except PathologyRequest.DoesNotExist:
        existing_request = None
        
    all_tests = PathologyTest.objects.all().order_by('order', 'id')
    
    return render(request, 'pathology/request_form.html', {
        'visit': visit,
        'existing_request': existing_request,
        'all_tests': all_tests,
    })

@login_required
def pathology_dashboard(request):
    date_str = request.GET.get('date', '')
    if date_str:
        try:
            from datetime import datetime
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            filter_date = timezone.localdate()
    else:
        filter_date = timezone.localdate()

    requests = PathologyRequest.objects.filter(
        date_of_request__date=filter_date
    ).select_related('visit__patient', 'requesting_physician').prefetch_related('tests').order_by('-date_of_request')

    return render(request, 'pathology/dashboard.html', {
        'requests': requests,
        'filter_date': filter_date,
    })

@login_required
@permission_required('pathology.change_pathologyrequest', raise_exception=True)
def pathology_result_input(request, request_uuid):
    patho_req = get_object_or_404(PathologyRequest, uuid=request_uuid)
    
    if request.method == 'POST':
        status = request.POST.get('status', 'PENDING')
        result_text = request.POST.get('result_text', '')
        notes = request.POST.get('notes', '')
        
        patho_req.status = status
        patho_req.processed_by = request.user
        patho_req.save()
        
        if status in ['IN_PROGRESS', 'COMPLETED']:
            from .models import PathologyResult
            result, created = PathologyResult.objects.get_or_create(
                pathology_request=patho_req,
                defaults={'verified_by': request.user}
            )
            result.result_text = result_text
            result.notes = notes
            result.verified_by = request.user
            
            if 'attachment' in request.FILES:
                result.attachment = request.FILES['attachment']
            
            if status == 'COMPLETED':
                result.completed_at = timezone.now()
            
            result.save()
            
            from .models import PathologyResultAttachment
            for f in request.FILES.getlist('attachments'):
                PathologyResultAttachment.objects.create(pathology_result=result, file=f)
        
        from medical_records.utils import log_visit_action
        log_visit_action(patho_req.visit, 'PATHO_RESULT', request.user)
        messages.success(request, _("Pathology result updated successfully."))
        return redirect('pathology_dashboard')
    
    try:
        existing_result = patho_req.result
    except ObjectDoesNotExist:
        existing_result = None
    
    return render(request, 'pathology/result_form.html', {
        'pathology_request': patho_req,
        'existing_result': existing_result,
    })
