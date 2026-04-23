from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from medical_records.models import Visit
from .models import RadiologyRequest, RadiologyTest

@login_required
@permission_required('radiology.add_radiologyrequest', raise_exception=True)
def radiology_request_create(request, visit_uuid):
    visit = get_object_or_404(Visit, uuid=visit_uuid)
    
    if request.method == 'POST':
        selected_test_ids = request.POST.getlist('tests')
        
        is_emergency = visit.current_room and visit.current_room.code in ['IGD', 'EMERGENCY']
        radiology_req, created = RadiologyRequest.objects.get_or_create(
            visit=visit,
            defaults={
                'requesting_physician': request.user,
                'source': 'IGD' if is_emergency else 'OPD'
            }
        )
        
        if not created:
            radiology_req.requesting_physician = request.user
            radiology_req.save()
            
        if selected_test_ids:
            tests = RadiologyTest.objects.filter(id__in=selected_test_ids)
            radiology_req.tests.set(tests)
        else:
            radiology_req.tests.clear()
            
        from medical_records.utils import log_visit_action
        log_visit_action(visit, 'RAD_REQUEST', request.user)
        messages.success(request, _("Radiology Referral saved successfully."))
        return redirect('perform_examination', visit_uuid=visit.uuid)
        
    try:
        existing_request = visit.radiology_request
    except RadiologyRequest.DoesNotExist:
        existing_request = None
        
    all_tests = RadiologyTest.objects.all().order_by('order', 'id')
    
    return render(request, 'radiology/request_form.html', {
        'visit': visit,
        'existing_request': existing_request,
        'all_tests': all_tests,
    })

@login_required
@permission_required('radiology.change_radiologyrequest', raise_exception=True)
def radiology_result_input(request, request_uuid):
    rad_req = get_object_or_404(RadiologyRequest, uuid=request_uuid)
    
    if request.method == 'POST':
        status = request.POST.get('status', 'PENDING')
        findings = request.POST.get('findings', '')
        impression = request.POST.get('impression', '')
        notes = request.POST.get('notes', '')
        
        rad_req.status = status
        rad_req.performed_by = request.user
        rad_req.save()
        
        if status in ['IN_PROGRESS', 'COMPLETED']:
            from .models import RadiologyResult
            result, created = RadiologyResult.objects.get_or_create(
                radiology_request=rad_req,
                defaults={'verified_by': request.user}
            )
            result.findings = findings
            result.impression = impression
            result.notes = notes
            result.verified_by = request.user
            
            if 'attachment' in request.FILES:
                result.attachment = request.FILES['attachment']
            
            if status == 'COMPLETED':
                result.completed_at = timezone.now()
            
            result.save()
            
            from .models import RadiologyResultAttachment
            for f in request.FILES.getlist('attachments'):
                RadiologyResultAttachment.objects.create(radiology_result=result, file=f)
        
        from medical_records.utils import log_visit_action
        log_visit_action(rad_req.visit, 'RAD_RESULT', request.user)
        messages.success(request, _("Radiology result updated successfully."))
        return redirect('radiology_dashboard')
    
    try:
        existing_result = rad_req.result
    except ObjectDoesNotExist:
        existing_result = None
    
    return render(request, 'radiology/result_form.html', {
        'radiology_request': rad_req,
        'existing_result': existing_result,
    })

@login_required
def radiology_dashboard(request):
    date_str = request.GET.get('date', '')
    if date_str:
        try:
            from datetime import datetime
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            filter_date = timezone.localdate()
    else:
        filter_date = timezone.localdate()

    requests = RadiologyRequest.objects.filter(
        date_of_request__date=filter_date
    ).select_related('visit__patient', 'requesting_physician').prefetch_related('tests').order_by('-date_of_request')

    return render(request, 'radiology/dashboard.html', {
        'requests': requests,
        'filter_date': filter_date,
    })
