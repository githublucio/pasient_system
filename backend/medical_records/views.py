from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
from django.utils.translation import gettext as _
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required

from .models import Visit, Diagnosis, Room, EmergencyObservation, EmergencyMedication
from .forms import (
    ExaminationForm, TriageForm, EmergencyExaminationForm,
    EmergencyAdmissionUpdateForm, EmergencyObservationForm,
    EmergencyMedicationForm, EmergencyDischargeForm
)
from .utils import log_visit_action

@login_required
@permission_required('medical_records.add_visit', raise_exception=True)
def emergency_direct_registration(request):
    """Fast-track registration specifically for Emergency Room direct arrivals."""
    from patients.models import Patient, DailyQueue
    from patients.forms import PatientRegistrationForm
    from django.db.models import Q
    
    query = request.GET.get('q', '').strip()
    patients = []
    if query:
        patients = Patient.objects.filter(
            Q(full_name__icontains=query) | 
            Q(patient_id__icontains=query) |
            Q(phone_number__icontains=query)
        )[:10]

    if request.method == 'POST' and 'register_new' in request.POST:
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            from django.db.models import Max
            year = timezone.localdate().year
            prefix = f"MD{year}"
            last_patient = Patient.objects.filter(patient_id__startswith=prefix).aggregate(
                max_id=Max('patient_id')
            )
            if last_patient['max_id']:
                last_num = int(last_patient['max_id'][-4:])
                new_num = last_num + 1
            else:
                new_num = 1
            patient.patient_id = f"{prefix}{new_num:04d}"
            patient.save()
            
            # Auto create visit to Emergency with arrival details
            arrival_mode = request.POST.get('arrival_mode', 'WALK_IN')
            brought_by = request.POST.get('brought_by_name', '')
            emergency_room = Room.objects.filter(code='IGD').first() or Room.objects.filter(code='EMERGENCY').first()
            queue, created = DailyQueue.objects.get_or_create(date=timezone.localdate(), department='General')
            
            visit = Visit.objects.create(
                patient=patient,
                current_room=emergency_room,
                status='IP',
                queue_number=queue.get_next_number(),
                checked_in_by=request.user,
                doctor=request.user,
                arrival_mode=arrival_mode,
                brought_by_name=brought_by,
                patient_type='FOUN'
            )
            log_visit_action(visit, 'CHECK_IN', request.user, room=emergency_room)
            messages.success(request, _("Patient %(name)s registered and admitted to Emergency.") % {'name': patient.full_name})
            return redirect('perform_examination', visit_uuid=visit.uuid)
    
    elif request.method == 'POST' and 'select_patient' in request.POST:
        patient_uuid = request.POST.get('patient_uuid')
        patient = get_object_or_404(Patient, uuid=patient_uuid)
        
        # Auto create visit to Emergency
        emergency_room = Room.objects.filter(code='IGD').first() or Room.objects.filter(code='EMERGENCY').first()
        queue, created = DailyQueue.objects.get_or_create(date=timezone.localdate(), department='General')
        
        visit = Visit.objects.create(
            patient=patient,
            current_room=emergency_room,
            status='IP',
            queue_number=queue.get_next_number(),
            checked_in_by=request.user,
            doctor=request.user,
            arrival_mode=request.POST.get('arrival_mode', 'WALK_IN'),
            brought_by_name=request.POST.get('brought_by_name', ''),
            companion_name=request.POST.get('companion_name', ''),
            patient_type='TUAN'
        )
        log_visit_action(visit, 'CHECK_IN', request.user, room=emergency_room)
        messages.success(request, _("Visit started for %(name)s in Emergency.") % {'name': patient.full_name})
        return redirect('perform_examination', visit_uuid=visit.uuid)

    next_id = Patient.generate_next_id()
    registration_form = PatientRegistrationForm(initial={'patient_id': next_id})
    return render(request, 'medical_records/emergency_direct_registration.html', {
        'patients': patients,
        'query': query,
        'registration_form': registration_form,
    })


@login_required
@permission_required('medical_records.view_menu_medical_records', raise_exception=True)
def triage_dashboard(request):
    """Room 2: Triage Dashboard for nurses."""
    query = request.GET.get('q', '')
    today = timezone.localdate()
    
    # Base filter for Room 2 waiting:
    # - Include 'In Progress' visits from any day (to allow follow-up)
    # - Include 'Scheduled' visits ONLY for today (to avoid no-show clutter)
    waiting_visits = Visit.objects.visible_to(request.user).filter(
        current_room__code__in=['TRIAGE', 'ROOM_2'],
    ).filter(
        Q(status='IP') | Q(status='SCH', visit_date__date=today)
    ).select_related('patient', 'current_room')
    
    # If search used
    search_results = None
    if query:
        search_results = Visit.objects.filter(
            Q(patient__full_name__icontains=query) | Q(patient__patient_id__icontains=query),
            visit_date__date=today
        ).select_related('patient', 'current_room').order_by('queue_number')[:50]
    
    waiting_visits = waiting_visits.order_by('queue_number')
    
    completed_today = Visit.objects.visible_to(request.user).filter(
        visit_date__date=today,
        current_room__order__gt=2
    ).exclude(current_room__code__in=['IGD', 'EMERGENCY']).select_related('patient', 'current_room').order_by('-visit_date')[:100]
    
    return render(request, 'medical_records/triage_dashboard.html', {
        'waiting_visits': waiting_visits,
        'completed_today': completed_today,
        'search_results': search_results,
        'query': query,
        'stats': {
            'waiting': waiting_visits.count(),
            'completed': completed_today.count(),
        }
    })

@login_required
@permission_required('medical_records.change_visit', raise_exception=True)
def triage_input(request, visit_uuid):
    """Room 2: Triage Input Form."""
    from django.shortcuts import get_object_or_404
    from .utils import log_visit_action
    visit = get_object_or_404(Visit, uuid=visit_uuid)
    
    if request.method == 'POST':
        form = TriageForm(request.POST, instance=visit)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.triage_nurse = request.user
            visit.save()
            log_visit_action(visit, 'TRIAGE', request.user, room=visit.current_room)
            messages.success(request, _("Triage for %(name)s completed. Patient directed to %(room)s.") % {
                'name': visit.patient.full_name,
                'room': visit.current_room.name
            })
            return redirect('triage_dashboard')
    else:
        form = TriageForm(instance=visit)
        if visit.current_room and visit.current_room.code not in ['TRIAGE', 'ROOM_2']:
             # If already triaged, warn user
             messages.warning(request, _("This patient has already been triaged."))
             
    return render(request, 'medical_records/triage_form.html', {
        'visit': visit,
        'form': form,
    })

@login_required
@permission_required('medical_records.view_menu_medical_records', raise_exception=True)
def doctor_dashboard(request):
    today = timezone.localdate()
    room_filter = request.GET.get('room', '')  # e.g. ?room=KIA
    search_query = request.GET.get('q', '').strip()

    # Rooms that should appear in the general OPD dashboard
    general_rooms = ['DOKTER', 'ROOM_3', 'ROOM_4', 'ROOM_5', 'ROOM_6']
    
    # Specialized rooms that require explicit selection
    specialist_rooms = ['KIA', 'HIV', 'TB', 'DENTAL', 'NUTRISI', 'USG']
    
    all_clinical_rooms = general_rooms + specialist_rooms

    # Role-based room default for non-admins
    if not room_filter and not request.user.is_superuser:
        if hasattr(request.user, 'staff_profile'):
            dept_code = request.user.staff_profile.department.code.upper()
            if dept_code in specialist_rooms:
                room_filter = dept_code
            elif dept_code in general_rooms:
                room_filter = dept_code

    if room_filter and room_filter in all_clinical_rooms:
        # Show only patients in that specific specialist room
        room_codes = [room_filter]
        page_title = Room.objects.filter(code=room_filter).values_list('name', flat=True).first() or room_filter
    else:
        # Default: show ONLY general clinical rooms
        room_codes = general_rooms
        page_title = _("General Consultation")

    # Show pending/in-progress patients:
    # - Include 'In Progress' (IP) from any date to ensure continuity.
    # - Include 'Scheduled' (SCH) only for today.
    waiting_visits_qs = Visit.objects.visible_to(request.user).filter(
        Q(current_room__code__in=room_codes) |
        Q(doctor=request.user, status='IP')
    ).filter(
        Q(status='IP') | Q(status='SCH', visit_date__date=today)
    ).distinct()

    if search_query:
        waiting_visits_qs = waiting_visits_qs.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(patient__patient_id__icontains=search_query)
        )

    waiting_visits = waiting_visits_qs.select_related('patient', 'current_room', 'doctor').order_by('queue_number')

    completed_visits = Visit.objects.visible_to(request.user).filter(
        current_room__code__in=room_codes,
        visit_date__date=today,
        status='COM'
    ).select_related('patient', 'current_room', 'doctor').order_by('-visit_date')[:100]

    room_counts = Visit.objects.visible_to(request.user).filter(
        current_room__code__in=room_codes,
        visit_date__date=today
    )

    # Cumulative totals for specific departments (e.g. HIV)
    total_patients_overall = 0
    if room_filter == 'HIV':
        from patients.models import Patient
        total_patients_overall = Patient.objects.filter(is_hiv_patient=True).count()

    return render(request, 'medical_records/doctor_dashboard.html', {
        'waiting_visits': waiting_visits,
        'completed_visits': completed_visits,
        'room_filter': room_filter,
        'page_title': page_title,
        'stats': {
            'total_today': room_counts.count(),
            'pending_today': waiting_visits_qs.count(),
            'completed_today': room_counts.filter(status='COM').count(),
            'total_overall': total_patients_overall,
        }
    })

@login_required
@permission_required('medical_records.view_menu_medical_records', raise_exception=True)
def emergency_dashboard(request):
    """Room: EMERGENCY Dashboard for critical care."""
    today = timezone.localdate()
    
    # Filter for active Emergency cases:
    # 1. Patients physically in IGD/EMERGENCY rooms
    # 2. Patients in auxiliary rooms (Lab, Rad, etc.) who have ER-specific vitals recorded (indicating they are from ER)
    waiting_visits_qs = Visit.objects.visible_to(request.user).filter(
        status__in=['SCH', 'IP']
    ).filter(
        Q(current_room__code__in=['IGD', 'EMERGENCY']) | 
        Q(source='IGD')
    ).select_related('patient', 'current_room').distinct()
    
    waiting_visits = waiting_visits_qs.order_by('queue_number')
    
    # Calculate observation duration for each visit
    for v in waiting_visits:
        v.observation_hours = (timezone.now() - v.visit_date).total_seconds() / 3600
        v.needs_referral = v.observation_hours > 24
    
    completed_today = Visit.objects.visible_to(request.user).filter(
        visit_date__date=today,
        current_room__code__in=['IGD', 'EMERGENCY'],
        status='COM'
    ).select_related('patient', 'current_room').order_by('-visit_date')[:100]
    
    # Emergency Stats
    room_counts = Visit.objects.visible_to(request.user).filter(
        current_room__code__in=['IGD', 'EMERGENCY'],
        visit_date__date=today
    )

    # Role detection
    is_nurse = False
    if hasattr(request.user, 'staff_profile'):
        is_nurse = request.user.staff_profile.category.name.upper() == 'PARAMEDIS'

    return render(request, 'medical_records/emergency_dashboard.html', {
        'waiting_visits': waiting_visits,
        'completed_today': completed_today,
        'stats': {
            'active_cases': waiting_visits.count(),
            'total_today': room_counts.count(),
            'discharged_today': room_counts.filter(status='COM').count(),
        },
        'is_nurse': is_nurse,
    })


@login_required
@permission_required('medical_records.view_menu_medical_records', raise_exception=True)
def emergency_triage_dashboard(request):
    """Dashboard specifically for ER Vitals/Triage check."""
    today = timezone.localdate()
    # Show patients in ER queue who haven't had their 'Emergency Re-check' vitals yet
    # Or just all active ER cases for triage
    waiting_visits = Visit.objects.visible_to(request.user).filter(
        current_room__code__in=['IGD', 'EMERGENCY'],
        status__in=['SCH', 'IP']
    ).select_related('patient', 'current_room').order_by('queue_number')
    
    # Simple check: if er_bp_sys is null, they definitely need triage
    for v in waiting_visits:
        v.needs_vitals = v.er_bp_sys is None
        
    return render(request, 'medical_records/emergency_triage_dashboard.html', {
        'waiting_visits': waiting_visits,
        'stats': {
            'waiting': waiting_visits.count(),
        }
    })


@login_required
@permission_required('medical_records.change_visit', raise_exception=True)
def emergency_triage_input(request, visit_uuid):
    """Focused triage/vitals input for Emergency Room."""
    visit = get_object_or_404(Visit, uuid=visit_uuid)
    from .forms import EmergencyExaminationForm
    
    if request.method == 'POST':
        # We use a subset of the EmergencyExaminationForm or a dedicated one.
        # For simplicity and consistency, we can reuse it but only show vitals in the template.
        form = EmergencyExaminationForm(request.POST, instance=visit)
        if form.is_valid():
            # If a nurse is doing this, we shouldn't finalize the examination
            # but we can save the vitals.
            v = form.save(commit=False)
            v.triage_nurse = request.user
            v.status = 'IP' # Ensure it stays in progress for the doctor
            v.save()
            form.save_m2m()
            
            from .utils import log_visit_action
            log_visit_action(v, 'TRIAGE', request.user, room=v.current_room)
            messages.success(request, _("ER Vitals for %(name)s recorded.") % {'name': v.patient.full_name})
            return redirect('emergency_triage_dashboard')
    else:
        form = EmergencyExaminationForm(instance=visit)
        
    return render(request, 'medical_records/emergency_triage_form.html', {
        'visit': visit,
        'form': form,
    })


@login_required
@permission_required('medical_records.change_visit', raise_exception=True)
def record_emergency_observation(request, visit_uuid):
    """Record hourly/periodic vitals in ER."""
    visit = get_object_or_404(Visit, uuid=visit_uuid)
    if request.method == 'POST':
        form = EmergencyObservationForm(request.POST)
        if form.is_valid():
            obs = form.save(commit=False)
            obs.visit = visit
            if not obs.checked_by:
                obs.checked_by = request.user
            obs.save()
            messages.success(request, _("Observation recorded for %(name)s.") % {'name': visit.patient.full_name})
            return redirect('perform_examination', visit_uuid=visit.uuid)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Observation Error - {field}: {error}")
    return redirect('perform_examination', visit_uuid=visit.uuid)


@login_required
@permission_required('medical_records.change_visit', raise_exception=True)
def administer_emergency_medication(request, visit_uuid):
    """Administer medication and deduct from Pharmacy stock immediately."""
    from django.db import transaction
    visit = get_object_or_404(Visit, uuid=visit_uuid)
    
    if request.method == 'POST':
        form = EmergencyMedicationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                med_admin = form.save(commit=False)
                med_admin.visit = visit
                
                if not med_admin.given_by:
                    med_admin.given_by = request.user
                
                if not med_admin.ordered_by:
                    med_admin.ordered_by = visit.doctor
                
                # STOCK DEDUCTION LOGIC
                medicine = med_admin.medicine
                if medicine.stock >= med_admin.quantity:
                    medicine.stock -= med_admin.quantity
                    medicine.save()
                    med_admin.save()
                    
                    log_visit_action(visit, 'PRESCRIPTION', request.user, 
                                     notes=f"Administered {med_admin.quantity} {medicine.name} ({med_admin.get_admin_type_display()})")
                    
                    messages.success(request, _("%(qty)d x %(med)s administered and stock updated.") % {
                        'qty': med_admin.quantity, 'med': medicine.name
                    })
                else:
                    messages.error(request, _("Insufficient stock for %(med)s. Current: %(stock)d") % {
                        'med': medicine.name, 'stock': medicine.stock
                    })
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Medication Error - {field}: {error}")
                    
    return redirect('perform_examination', visit_uuid=visit.uuid)

@login_required
@permission_required('medical_records.view_menu_medical_records', raise_exception=True)
def staff_performance_report(request):
    """Report on staff activity and patient outcomes (Success vs Referral)."""
    from django.db.models import Count, Q
    
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    today = timezone.localdate()
    if not date_from:
        date_from = today.replace(day=1).isoformat() # Beginning of month
    if not date_to:
        date_to = today.isoformat()
        
    # Get all visits in range
    visits = Visit.objects.visible_to(request.user).filter(
        visit_date__date__gte=date_from,
        visit_date__date__lte=date_to
    ).select_related('patient', 'doctor', 'triage_nurse', 'checked_in_by', 'current_room')
    
    # Global Aggregates
    total_count = visits.count()
    completed_clinic = visits.filter(status='COM', refer_to_central=False).count()
    referred_count = visits.filter(refer_to_central=True).count()
    
    # Staff Metrics - Doctors
    doctor_stats = visits.values(
        'doctor__username', 'doctor__first_name', 'doctor__last_name'
    ).annotate(
        total=Count('uuid'),
        completed=Count('uuid', filter=Q(status='COM', refer_to_central=False)),
        referred=Count('uuid', filter=Q(refer_to_central=True)),
        in_progress=Count('uuid', filter=Q(status='IP')),
    ).exclude(doctor__isnull=True).order_by('-total')
    
    # Staff Metrics - Nurses (Triage)
    nurse_stats = visits.values(
        'triage_nurse__username', 'triage_nurse__first_name', 'triage_nurse__last_name'
    ).annotate(
        total=Count('uuid')
    ).exclude(triage_nurse__isnull=True).order_by('-total')
    
    # Staff Metrics - Reception (Check-in)
    reception_stats = visits.values(
        'checked_in_by__username', 'checked_in_by__first_name', 'checked_in_by__last_name'
    ).annotate(
        total=Count('uuid')
    ).exclude(checked_in_by__isnull=True).order_by('-total')

    return render(request, 'medical_records/staff_performance_report.html', {
        'date_from': date_from,
        'date_to': date_to,
        'total_count': total_count,
        'completed_clinic': completed_clinic,
        'referred_count': referred_count,
        'doctor_stats': doctor_stats,
        'nurse_stats': nurse_stats,
        'reception_stats': reception_stats,
        'recent_visits': visits.order_by('-visit_date')[:100],
    })

@login_required
@permission_required('medical_records.view_menu_medical_records', raise_exception=True)
def disease_statistics_report(request):
    """
    Statistics report grouped by hierarchical diagnoses.
    Shows totals for parent diagnoses and breakdowns for sub-types.
    """
    from django.db.models import Count, Q
    from django.utils import timezone
    
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    today = timezone.localdate()
    if not date_from:
        date_from = today.replace(day=1).isoformat()
    if not date_to:
        date_to = today.isoformat()
        
    visits = Visit.objects.visible_to(request.user).filter(
        visit_date__date__gte=date_from,
        visit_date__date__lte=date_to,
        diagnosis__isnull=False
    )
    
    # Get all root diagnoses (those without a parent)
    roots = Diagnosis.objects.filter(parent__isnull=True).order_by('code')
    
    report_data = []
    
    for root in roots:
        # Get all related IDs for this branch (root + children recursive)
        related_ids = root.get_related_ids()
        root_count = visits.filter(diagnosis_id=root.id).count()
        child_total = visits.filter(diagnosis_id__in=related_ids).exclude(diagnosis_id=root.id).count()
        total_count = root_count + child_total
        
        if total_count > 0:
            # Breakdown of sub-types
            # We filter visits that have a diagnosis belonging to this root's descendants
            breakdown = visits.filter(diagnosis_id__in=related_ids).exclude(diagnosis_id=root.id).values(
                'diagnosis__code', 'diagnosis__name'
            ).annotate(count=Count('uuid')).order_by('-count')
            
            report_data.append({
                'root': root,
                'total': total_count,
                'root_only': root_count,
                'breakdown': breakdown
            })
            
    return render(request, 'medical_records/disease_report.html', {
        'date_from': date_from,
        'date_to': date_to,
        'report_data': report_data,
    })

@login_required
@permission_required('medical_records.change_visit', raise_exception=True)
def perform_examination(request, visit_uuid):
    from django.shortcuts import get_object_or_404
    visit = get_object_or_404(Visit, uuid=visit_uuid)
    
    # Only show emergency forms/features if the patient is actually in the Emergency room (IGD/EMERGENCY).
    # We remove the 'or not visit.triage_nurse' check to avoid treating all direct-admissions (like HIV/TB) as emergency.
    is_emergency = visit.current_room and visit.current_room.code in ['IGD', 'EMERGENCY']
    
    # Role-based detection
    is_nurse = False
    if hasattr(request.user, 'staff_profile'):
        is_nurse = request.user.staff_profile.category.name.upper() == 'PARAMEDIS'
    
    FormClass = EmergencyExaminationForm if is_emergency else ExaminationForm


    
    if request.method == 'POST':
        # --- Handle Specialized ER Modals ---
        action = request.POST.get('action')
        
        if action == 'update_admission' and is_emergency:
            adm_form = EmergencyAdmissionUpdateForm(request.POST, instance=visit)
            if adm_form.is_valid():
                adm_form.save()
                messages.success(request, _("Admission details updated."))
                return redirect('perform_examination', visit_uuid=visit.uuid)

        if action == 'discharge_patient' and is_emergency:
            dis_form = EmergencyDischargeForm(request.POST, instance=visit)
            if dis_form.is_valid():
                v = dis_form.save(commit=False)
                v.status = 'COM'
                v.discharge_datetime = timezone.now()
                v.save()
                
                if v.follow_up_date:
                    from appointments.models import Appointment
                    import datetime

                    auto_notes = v.follow_up_notes if v.follow_up_notes else _("Automated follow-up from Emergency Room")
                    
                    # PRIVACY POLICY (Option B):
                    # If the patient is an HIV patient, route the follow-up appointment
                    # to the HIV department room — NOT the IGD room.
                    # This ensures follow-up appointments for HIV patients never appear
                    # in the general appointment calendar.
                    if v.patient.is_hiv_patient:
                        hiv_room = Room.objects.filter(code='HIV').first()
                        appt_room = hiv_room if hiv_room else v.current_room
                        appt_reason = f"[HIV Follow-Up] {auto_notes}"
                    else:
                        appt_room = v.current_room
                        appt_reason = f"Follow-Up: {auto_notes}"

                    Appointment.objects.get_or_create(
                        patient=v.patient,
                        appointment_date=v.follow_up_date,
                        doctor=v.doctor,
                        defaults={
                            'department': appt_room,
                            'appointment_time': datetime.time(9, 0),
                            'reason': appt_reason,
                            'created_by': request.user,
                        }
                    )

                log_visit_action(v, 'COMPLETED', request.user)
                
                if v.patient.is_hiv_patient and v.follow_up_date:
                    messages.success(request, _(
                        "Patient discharged from Emergency. Follow-up appointment has been registered in the HIV Department schedule (%(date)s)."
                    ) % {'date': v.follow_up_date.strftime('%d %b %Y')})
                else:
                    messages.success(request, _("Patient discharged from Emergency."))
                    
                return redirect('emergency_dashboard')

        # --- Standard Main Form Handling ---
        form = FormClass(request.POST, instance=visit)
        if form.is_valid():
            # Process multiple referrals
            referral_rooms = list(form.cleaned_data.get('referral_rooms', []))
            original_room = visit.current_room

            if is_nurse:
                # Nurses can only update specific fields (Vitals, Lab Request)
                # We strictly prevent them from changing Diagnosis or Clinical Notes 
                # if those were already set by a doctor, or if they try to set them.
                visit.diagnosis = visit.__class__.objects.get(pk=visit.pk).diagnosis
                visit.clinical_notes = visit.__class__.objects.get(pk=visit.pk).clinical_notes
                visit.save()
            else:
                # Doctors have full control
                visit.doctor = request.user
                visit = form.save(commit=False)
                
                # Update current_room to the first selected referral room (if any)
                if referral_rooms:
                    visit.current_room = referral_rooms[0]
                    
                visit.doctor = request.user
                visit.save()
                form.save_m2m()

            if visit.follow_up_date:
                from appointments.models import Appointment
                import datetime
                auto_notes = visit.follow_up_notes if visit.follow_up_notes else "Automated follow-up"
                Appointment.objects.get_or_create(
                    patient=visit.patient,
                    appointment_date=visit.follow_up_date,
                    doctor=visit.doctor,
                    defaults={
                        'department': visit.current_room,
                        'appointment_time': datetime.time(9, 0),
                        'reason': f"Follow-Up / Automated: {auto_notes}",
                        'created_by': request.user
                    }
                )

            # --- Allergy Sync Logic ---
            allergy_str = form.cleaned_data.get('allergy_noted')
            if allergy_str:
                from patients.models import PatientAllergy
                PatientAllergy.objects.get_or_create(
                    patient=visit.patient,
                    allergen=allergy_str,
                    defaults={'reaction': _('Noted during ER visit')}
                )
                messages.info(request, _("Allergy '%s' added to patient record.") % allergy_str)

            # --- Unified Diagnostic Referral Logic ---
            source_tag = 'IGD' if is_emergency else 'OPD'
            
            # Universal source tracking on the Visit model
            if visit.source != source_tag:
                visit.source = source_tag
                visit.save()

            referred_to_lab = visit.lab_cbc
            referred_to_rad = False
            referred_to_pharm = getattr(visit, 'pharmacy_requested', False)
            referred_to_patho = False

            for room in referral_rooms:
                if 'LAB' in room.name.upper() or 'LAB' in room.code.upper() or room.code == 'ROOM_7':
                    referred_to_lab = True
                elif 'RADIOLOGY' in room.code.upper() or 'RAD' in room.code.upper():
                    referred_to_rad = True
                elif 'PHARM' in room.name.upper() or 'PHARM' in room.code.upper() or room.code == 'ROOM_8':
                    referred_to_pharm = True
                elif 'PATHOLOGY' in room.code.upper() or 'PATHO' in room.code.upper():
                    referred_to_patho = True

            # 1. Laboratory Request
            if referred_to_lab:
                from laboratory.models import LabRequest, LabTest
                lab_req, created = LabRequest.objects.get_or_create(
                    visit=visit,
                    defaults={
                        'requesting_physician': request.user,
                        'source': source_tag
                    }
                )
                if not created:
                    lab_req.source = source_tag
                    lab_req.requesting_physician = request.user
                    lab_req.save()

                if visit.lab_cbc:
                    try:
                        cbc_test = LabTest.objects.get(name__iexact='CBC')
                        lab_req.tests.add(cbc_test)
                    except LabTest.DoesNotExist:
                        pass
            
            # 2. Pharmacy / Prescription
            if referred_to_pharm:
                from pharmacy.models import Prescription
                presc, created = Prescription.objects.get_or_create(
                    visit=visit,
                    defaults={
                        'doctor': request.user,
                        'source': source_tag
                    }
                )
                if not created:
                    presc.source = source_tag
                    presc.doctor = request.user
                    presc.save()

            # 3. Radiology Request
            if referred_to_rad:
                from radiology.models import RadiologyRequest
                RadiologyRequest.objects.get_or_create(
                    visit=visit,
                    defaults={
                        'requesting_physician': request.user,
                        'source': source_tag
                    }
                )

            # 4. Pathology Request
            if referred_to_patho:
                from pathology.models import PathologyRequest
                PathologyRequest.objects.get_or_create(
                    visit=visit,
                    defaults={
                        'requesting_physician': request.user,
                        'source': source_tag
                    }
                )

            log_visit_action(visit, 'COMPLETED' if visit.status == 'COM' else 'EXAMINATION', request.user, room=visit.current_room)

            if visit.refer_to_central:
                log_visit_action(visit, 'REFERRED', request.user)

            if is_emergency:
                dept_names = ", ".join([r.name for r in referral_rooms]) if referral_rooms else _("None")
                messages.success(request, _("Data examination for %(name)s saved. Referral sent to %(dept)s. Patient remains in Emergency queue.") % {
                    'name': visit.patient.full_name,
                    'dept': dept_names,
                })
            else:
                messages.success(request, _("Examination for %(name)s saved. Patient referred to %(room)s.") % {
                    'name': visit.patient.full_name,
                    'room': visit.current_room.name if visit.current_room else _("None")
                })

            if visit.status == 'COM' or (referral_rooms and visit.current_room != original_room) or is_emergency:
                if is_emergency:
                    return redirect('emergency_dashboard')
                return redirect('doctor_dashboard')
            
            return redirect('perform_examination', visit_uuid=visit.uuid)

    else:
        form = FormClass(instance=visit)
    
    enrich_visit_lab_results(visit)

    # Prepare extra forms for Emergency cases
    context = {
        'visit': visit,
        'form': form,
        'is_emergency': is_emergency,
        'is_nurse': is_nurse,
    }

    if is_emergency:
        context['obs_form'] = EmergencyObservationForm(initial={'check_time': timezone.now(), 'checked_by': request.user})
        context['med_form'] = EmergencyMedicationForm(initial={'ordered_by': visit.doctor, 'given_by': request.user})
        context['adm_form'] = EmergencyAdmissionUpdateForm(instance=visit)
        context['dis_form'] = EmergencyDischargeForm(instance=visit)
        context['emergency_observations'] = visit.observations.all().order_by('-check_time')
        context['administered_medications'] = visit.emergency_medications.all().order_by('-given_at')

    # --- Enrich Diagnostic Data (Lab, Radiology, Images) ---
    enrich_visit_diagnostic_data(visit, context)

    return render(request, 'medical_records/examination.html', context)


def enrich_visit_diagnostic_data(visit, context):
    """Aggregates all diagnostic results, reports, and images for display."""
    # 1. Laboratory Results (Structured)
    lab_results = []
    if hasattr(visit, 'lab_results'):
        # Sort by most recent if needed, but usually linked to the visit
        lab_results = list(visit.lab_results.all().select_related('test_parameter'))
    context['lab_results'] = lab_results
    
    # 2. Radiology Results & Images
    radiology_data = {
        'request': None,
        'result': None,
        'images': []
    }
    
    if hasattr(visit, 'radiology_request'):
        rad_req = visit.radiology_request
        radiology_data['request'] = rad_req
        if hasattr(rad_req, 'result'):
            rad_res = rad_req.result
            radiology_data['result'] = rad_res
            # Fetch all attachments (gallery)
            radiology_data['images'] = list(rad_res.attachments.all())
            
    context['radiology_data'] = radiology_data


from laboratory.views import CBC_RANGES, SEROLOGY_PARAMS, BIOCHEMISTRY_PARAMS, URINALYSIS_PARAMS, MICROSCOPY_PARAMS, MICROBIOLOGY_PARAMS

def enrich_visit_lab_results(visit):
    lab_req = getattr(visit, 'lab_request', None)
    if lab_req and lab_req.status == 'COMPLETED':
        try:
            res = lab_req.result
            if not res or not res.result_data:
                return

            # 1. CBC Handling (Legacy or simple CBC only)
            cbc_data = res.result_data.get('cbc')
            if isinstance(cbc_data, dict):
                cat = res.result_data.get('category')
                ranges = CBC_RANGES.get(cat, {})
                cbc_list = []
                for k, v in cbc_data.items():
                    if v: # Only show non-empty values
                        cbc_list.append({
                            'param': str(k).upper(),
                            'value': v,
                            'range': ranges.get(k, '-')
                        })
                visit.cbc_structured_list = cbc_list

            # 2. Comprehensive Results Handling
            sections = [
                ('serology', SEROLOGY_PARAMS),
                ('biochemistry', BIOCHEMISTRY_PARAMS),
                ('urinalysis', URINALYSIS_PARAMS),
                ('microscopy', MICROSCOPY_PARAMS),
                ('microbiology', MICROBIOLOGY_PARAMS),
            ]
            
            visit.lab_categorized_results = {}
            for sec_key, params in sections:
                sec_data = res.result_data.get(sec_key)
                if isinstance(sec_data, dict) and any(sec_data.values()): # Only add if section has any data
                    current_sec_results = []
                    for p in params:
                        val_raw = sec_data.get(p['key'])
                        if val_raw:
                            val = val_raw.get('value') if isinstance(val_raw, dict) else val_raw
                            remark = val_raw.get('remark') if isinstance(val_raw, dict) else ''
                            if val: # Only show if there's a value
                                current_sec_results.append({
                                    'name': p['name'],
                                    'value': val,
                                    'remark': remark,
                                    'unit': p.get('unit', '-'),
                                    'range': p.get('range', '-')
                                })

                    if current_sec_results:
                        visit.lab_categorized_results[sec_key.title()] = current_sec_results
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error enriching lab results: {e}")
            pass

@login_required
@permission_required('medical_records.view_visit', raise_exception=True)
def visit_detail(request, visit_uuid):
    visit = get_object_or_404(
        Visit.objects.visible_to(request.user).select_related(
            'patient', 'doctor', 'checked_in_by', 'triage_nurse', 'current_room'
        ).prefetch_related('logs__performed_by', 'logs__room'),
        uuid=visit_uuid
    )
    enrich_visit_lab_results(visit)
    return render(request, 'medical_records/visit_detail.html', {
        'visit': visit,
    })

@login_required
def visit_detail_ajax(request, visit_uuid):
    visit = get_object_or_404(Visit.objects.visible_to(request.user), uuid=visit_uuid)
    enrich_visit_lab_results(visit)
    return render(request, 'medical_records/visit_detail_modal_content.html', {
        'visit': visit,
    })


@login_required
@permission_required('medical_records.add_visit', raise_exception=True)
def kia_direct_registration(request):
    """
    MCH (Maternal & Child Health) Direct Registration page.
    Supports:
    - GET: Show search + new patient registration form
    - POST (select_patient): Existing patient selected → go to category modal (via redirect with params)
    - POST (register_new): Register brand-new patient → create MCH Visit → examination
    - POST (kia_checkin): Called from patient_list modals for existing patients
    """
    from patients.models import Patient, DailyQueue
    from patients.forms import PatientRegistrationForm
    from django.db.models import Max

    category_labels = {
        'ANA_0_6':     _('MCH - Baby 0-6 Months'),
        'ANA_6_59':    _('MCH - Child 6-59 Months'),
        'IBU_MENYUSU': _('MCH - Breastfeeding Mother'),
        'IBU_HAMIL':   _('MCH - Pregnant Mother'),
    }

    def _get_kia_room():
        return (
            Room.objects.filter(code='KIA').first() or
            Room.objects.filter(name__icontains='KIA').first() or
            Room.objects.filter(name__icontains='Maternidade').first()
        )

    def _create_kia_visit(patient, category, patient_type, weight=None,
                          height=None, muac=None, companion=''):
        kia_room = _get_kia_room()
        if not kia_room:
            return None, _("MCH room not found. Ask admin to create it.")
        queue, _c = DailyQueue.objects.get_or_create(
            date=timezone.localdate(), department='MCH'
        )
        complaint = category_labels.get(category, _('MCH Visit'))
        visit = Visit.objects.create(
            patient=patient,
            current_room=kia_room,
            status='IP',
            queue_number=queue.get_next_number(),
            checked_in_by=request.user,
            doctor=request.user,
            patient_type=patient_type,
            complaint=complaint,
            weight=weight or None,
            muac=muac or None,
            companion_name=companion,
            vital_signs={'height_cm': height, 'kia_category': category},
        )
        log_visit_action(visit, 'CHECK_IN', request.user, room=kia_room)
        return visit, None

    # ── POST: existing patient from patient_list modals ──────────────
    if request.method == 'POST' and 'patient_uuid' in request.POST and 'kia_category' in request.POST:
        patient_uuid = request.POST.get('patient_uuid')
        category     = request.POST.get('kia_category', '')
        patient_type = request.POST.get('patient_type', 'TUAN')
        patient = get_object_or_404(Patient.objects.visible_to(request.user), uuid=patient_uuid)
        visit, err = _create_kia_visit(
            patient, category, patient_type,
            weight=request.POST.get('weight'),
            height=request.POST.get('height'),
            muac=request.POST.get('muac'),
            companion=request.POST.get('companion_name', ''),
        )
        if err:
            messages.error(request, err)
            return redirect('patient_list')
        messages.success(request, _("%(name)s → MCH Queue #%(q)s") % {
            'name': patient.full_name, 'q': visit.queue_number})
        return redirect('perform_examination', visit_uuid=visit.uuid)

    # ── POST: select existing patient from search results ────────────
    if request.method == 'POST' and 'select_patient' in request.POST:
        patient_uuid = request.POST.get('patient_uuid')
        category     = request.POST.get('kia_category', 'ANA_0_6')
        patient_type = request.POST.get('patient_type', 'TUAN')
        patient = get_object_or_404(Patient.objects.visible_to(request.user), uuid=patient_uuid)
        visit, err = _create_kia_visit(patient, category, patient_type)
        if err:
            messages.error(request, err)
            return redirect('kia_direct_registration')
        messages.success(request, _("%(name)s → MCH Queue #%(q)s") % {
            'name': patient.full_name, 'q': visit.queue_number})
        return redirect('perform_examination', visit_uuid=visit.uuid)

    # ── POST: register new patient + KIA visit ───────────────────────
    if request.method == 'POST' and 'register_new' in request.POST:
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            year   = timezone.localdate().year
            prefix = f"MD{year}"
            last = Patient.objects.filter(patient_id__startswith=prefix).aggregate(max_id=Max('patient_id'))
            
            # Safe parsing of the last ID number
            try:
                if last['max_id']:
                    new_num = int(last['max_id'][-4:]) + 1
                else:
                    new_num = 1
            except (ValueError, TypeError):
                new_num = 1
                
            patient.patient_id = f"{prefix}{new_num:04d}"
            
            category = request.POST.get('kia_category', 'ANA_0_6')
            if category == 'IBU_HAMIL':
                patient.is_pregnant = True
                patient.gender = 'F'  # Force female for pregnant
            elif category == 'IBU_MENYUSU':
                patient.is_lactating = True
                patient.gender = 'F'  # Force female for breastfeeding
                
            patient.save()

            patient_type = 'FOUN'  # always new
            visit, err = _create_kia_visit(
                patient, category, patient_type,
                weight=request.POST.get('weight'),
                height=request.POST.get('height'),
                muac=request.POST.get('muac'),
                companion=request.POST.get('companion_name', ''),
            )
            if err:
                messages.error(request, err)
                return redirect('kia_direct_registration')
            messages.success(request,
                _("New patient %(name)s registered and admitted to MCH. Queue #%(q)s.") % {
                    'name': patient.full_name, 'q': visit.queue_number})
            return redirect('perform_examination', visit_uuid=visit.uuid)
        # Form invalid — fall through to re-render with errors
        query = request.GET.get('q', '').strip()
        patients = []
        registration_form = form
        return render(request, 'medical_records/kia_direct_registration.html', {
            'registration_form': registration_form,
            'patients': patients,
            'query': query,
            'category_labels': category_labels,
        })

    # ── GET: show page ────────────────────────────────────────────────
    query = request.GET.get('q', '').strip()
    patients = []
    if query:
        patients = Patient.objects.visible_to(request.user).filter(
            Q(full_name__icontains=query) |
            Q(patient_id__icontains=query) |
            Q(phone_number__icontains=query)
        )[:10]

    next_id = Patient.generate_next_id()
    registration_form = PatientRegistrationForm(initial={'patient_id': next_id})
    return render(request, 'medical_records/kia_direct_registration.html', {
        'registration_form': registration_form,
        'patients': patients,
        'query': query,
        'category_labels': category_labels,
    })


# --- Diagnosis Master Data CRUD ---

class DiagnosisListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Diagnosis
    permission_required = 'medical_records.view_diagnosis'
    template_name = 'master_data/list.html'
    context_object_name = 'items'
    paginate_by = 50
    extra_context = {'title': _('Diagnosis List'), 'model_name': 'diagnosis'}

    def get_queryset(self):
        from django.db.models import Q
        queryset = super().get_queryset().select_related('parent').order_by('code')
        q = self.request.GET.get('q')
        show = self.request.GET.get('show')
        
        if show == 'parents':
            queryset = queryset.filter(parent__isnull=True)
            
        if q:
            queryset = queryset.filter(
                Q(code__icontains=q) | Q(name__icontains=q)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['show'] = self.request.GET.get('show', '')
        return context

@login_required
@permission_required('medical_records.view_diagnosis', raise_exception=True)
def export_diagnoses_pdf(request):
    from clinic_core.pdf_utils import render_to_pdf
    from django.db.models import Q
    from django.utils import timezone
    
    q = request.GET.get('q')
    queryset = Diagnosis.objects.select_related('parent').order_by('code')
    if q:
        queryset = queryset.filter(Q(code__icontains=q) | Q(name__icontains=q))
    
    context = {
        'items': queryset,
        'query': q,
        'today': timezone.now(),
        'clinic_name': _("Clinic Bairo Pite Lanud")
    }
    pdf = render_to_pdf('medical_records/pdf/diagnosis_list_pdf.html', context)
    if pdf:
        filename = f"Diagnosis_List_{timezone.now().strftime('%Y%m%d')}.pdf"
        pdf['Content-Disposition'] = f'attachment; filename="{filename}"'
        return pdf
    return HttpResponse("Error generating PDF", status=500)

@login_required
@permission_required('medical_records.view_diagnosis', raise_exception=True)
def export_diagnoses_excel(request):
    import openpyxl
    from openpyxl.styles import Font, Alignment
    from django.db.models import Q
    from django.http import HttpResponse
    from django.utils import timezone
    
    q = request.GET.get('q')
    queryset = Diagnosis.objects.select_related('parent').order_by('code')
    if q:
        queryset = queryset.filter(Q(code__icontains=q) | Q(name__icontains=q))
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Diagnoses"
    
    # Header
    headers = ["Diagnosis Code", "Description", "Parent Code"]
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
        
    # Data
    for row_num, item in enumerate(queryset, 2):
        ws.cell(row=row_num, column=1, value=item.code)
        ws.cell(row=row_num, column=2, value=item.name)
        ws.cell(row=row_num, column=3, value=item.parent.code if item.parent else "")
        
    # Column width
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 45
    ws.column_dimensions['C'].width = 15
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"Diagnosis_List_{timezone.now().strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response

class DiagnosisDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Diagnosis
    permission_required = 'medical_records.view_diagnosis'
    template_name = 'master_data/detail.html'
    context_object_name = 'item'
    extra_context = {'title': _('Diagnosis Detail'), 'model_name': 'diagnosis'}

class DiagnosisCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Diagnosis
    fields = ['code', 'name', 'parent']
    permission_required = 'medical_records.add_diagnosis'
    template_name = 'master_data/form.html'
    success_url = reverse_lazy('diagnosis_list')
    extra_context = {'title': _('Add New Diagnosis')}

class DiagnosisUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Diagnosis
    fields = ['code', 'name', 'parent']
    permission_required = 'medical_records.change_diagnosis'
    template_name = 'master_data/form.html'
    success_url = reverse_lazy('diagnosis_list')
    extra_context = {'title': _('Edit Diagnosis')}

class DiagnosisDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Diagnosis
    permission_required = 'medical_records.delete_diagnosis'
    template_name = 'master_data/confirm_delete.html'
    success_url = reverse_lazy('diagnosis_list')
    extra_context = {'title': _('Delete Diagnosis')}

# --- Room Master Data CRUD ---

class RoomListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Room
    permission_required = 'medical_records.view_room'
    template_name = 'master_data/list.html'
    context_object_name = 'items'
    extra_context = {'title': _('Clinic Rooms'), 'model_name': 'room'}

class RoomDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Room
    permission_required = 'medical_records.view_room'
    template_name = 'master_data/detail.html'
    context_object_name = 'item'
    extra_context = {'title': _('Room Detail'), 'model_name': 'room'}

class RoomCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Room
    fields = ['name', 'code', 'description', 'order']
    permission_required = 'medical_records.add_room'
    template_name = 'master_data/form.html'
    success_url = reverse_lazy('room_list')
    extra_context = {'title': _('Add New Room')}

class RoomUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Room
    fields = ['name', 'code', 'description', 'order']
    permission_required = 'medical_records.change_room'
    template_name = 'master_data/form.html'
    success_url = reverse_lazy('room_list')
    extra_context = {'title': _('Edit Room')}

class RoomDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Room
    permission_required = 'medical_records.delete_room'
    template_name = 'master_data/confirm_delete.html'
    success_url = reverse_lazy('room_list')
    extra_context = {'title': _('Delete Room')}

@login_required
@permission_required('medical_records.view_menu_medical_records', raise_exception=True)
def department_completed_list(request):
    """
    Shows a paginated list of all completed patients per department.
    Dept: emergency, triage, or the specific room code.
    """
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    dept = request.GET.get('dept', '')
    query = request.GET.get('q', '').strip()
    
    # NEW: Default to specialized dept if no dept specified and user belongs to that dept
    staff_profile = getattr(request.user, 'staff_profile', None)
    if not dept and staff_profile and staff_profile.department:
        dept_code = staff_profile.department.code.upper()
        if dept_code in ['HIV', 'AIDS']:
            dept = 'HIV'
        elif dept_code == 'NUTRISI':
            dept = 'NUTRISI'
    
    visits = Visit.objects.visible_to(request.user).select_related('patient', 'current_room').order_by('-visit_date')
    
    page_title = _("All Historical Visits")
    
    if dept == 'triage':
        visits = visits.filter(triage_nurse__isnull=False)
        page_title = _("Triage History")
    elif dept == 'emergency':
        visits = visits.filter(current_room__code__in=['IGD', 'EMERGENCY'], status__in=['COM', 'IP']).exclude(doctor__isnull=True)
        page_title = _("Emergency History")
    elif dept == 'HIV':
        # Master Log: Show ALL historical visits for any patient tagged as HIV
        visits = visits.filter(patient__is_hiv_patient=True, status='COM')
        page_title = _("Complete HIV Patients History")
    elif dept == 'NUTRISI':
        # Nutrition Master Log: Show visits for patients who are Pregnant, Lactating, or Children (<5 years)
        from dateutil.relativedelta import relativedelta
        today = timezone.localdate()
        child_limit = today - relativedelta(months=59)
        visits = visits.filter(
            Q(patient__is_pregnant=True) | 
            Q(patient__is_lactating=True) | 
            Q(patient__date_of_birth__gte=child_limit),
            status='COM'
        )
        page_title = _("Nutrition Patients Master History")
    elif dept:
        # For KIA, TB, Dental, etc (Room-specific history)
        visits = visits.filter(current_room__code=dept, status='COM')
        room_obj = Room.objects.filter(code=dept).first()
        if room_obj:
            page_title = f"{room_obj.name} - {_('History')}"
        else:
            page_title = f"{dept} - {_('History')}"
    else:
        # General completed
        visits = visits.filter(status='COM')
        
    if query:
        visits = visits.filter(
            Q(patient__full_name__icontains=query) | 
            Q(patient__patient_id__icontains=query)
        )
        
    paginator = Paginator(visits, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'medical_records/completed_list.html', {
        'page_obj': page_obj,
        'page_title': page_title,
        'dept': dept,
        'query': query,
    })

@login_required
@permission_required('medical_records.view_visit', raise_exception=True)
def export_visit_history_pdf(request):
    from django.db.models import Q
    from clinic_core.pdf_utils import render_to_pdf
    
    dept = request.GET.get('dept', '')
    query = request.GET.get('q', '').strip()
    visits = Visit.objects.visible_to(request.user).select_related('patient', 'current_room', 'doctor', 'diagnosis').order_by('-visit_date')
    
    page_title = _("All Visits")
    if dept == 'triage':
        visits = visits.filter(triage_nurse__isnull=False)
        page_title = _("Triage History")
    elif dept == 'HIV':
        visits = visits.filter(patient__is_hiv_patient=True, status='COM')
        page_title = _("HIV Patients History")
    elif dept == 'NUTRISI':
        from dateutil.relativedelta import relativedelta
        today = timezone.localdate()
        child_limit = today - relativedelta(months=59)
        visits = visits.filter(
            Q(patient__is_pregnant=True) | 
            Q(patient__is_lactating=True) | 
            Q(patient__date_of_birth__gte=child_limit),
            status='COM'
        )
        page_title = _("Nutrition Patients History")
    elif dept:
        visits = visits.filter(current_room__code=dept)
        room_obj = Room.objects.filter(code=dept).first()
        page_title = f"{room_obj.name} - {_('History')}" if room_obj else f"{dept} - {_('History')}"

    if query:
        visits = visits.filter(
            Q(patient__full_name__icontains=query) | 
            Q(patient__patient_id__icontains=query)
        )
    
    # We limit to 500 for PDF to avoid timeout, but usually history is paged
    visits = visits[:500]
    
    context = {
        'visits': visits,
        'page_title': page_title,
        'query': query,
    }
    pdf = render_to_pdf('medical_records/pdf/visit_history_pdf.html', context)
    if pdf:
        filename = f"Visit_History_{timezone.now().strftime('%Y%m%d')}.pdf"
        pdf['Content-Disposition'] = f'attachment; filename="{filename}"'
        return pdf
    return HttpResponse("Error generating PDF", status=500)

@login_required
@permission_required('medical_records.view_visit', raise_exception=True)
def export_visit_history_excel(request):
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    from django.db.models import Q

    dept = request.GET.get('dept', '')
    query = request.GET.get('q', '').strip()
    visits = Visit.objects.visible_to(request.user).select_related('patient', 'current_room', 'doctor', 'diagnosis').order_by('-visit_date')

    if dept == 'triage':
        visits = visits.filter(triage_nurse__isnull=False)
    elif dept == 'emergency':
        visits = visits.filter(current_room__code__in=['IGD', 'EMERGENCY'], status__in=['COM', 'IP']).exclude(doctor__isnull=True)
    elif dept == 'NUTRISI':
        from dateutil.relativedelta import relativedelta
        today = timezone.localdate()
        child_limit = today - relativedelta(months=59)
        visits = visits.filter(
            Q(patient__is_pregnant=True) | 
            Q(patient__is_lactating=True) | 
            Q(patient__date_of_birth__gte=child_limit),
            status='COM'
        )
    elif dept:
        visits = visits.filter(current_room__code=dept)

    if query:
        visits = visits.filter(
            Q(patient__full_name__icontains=query) | 
            Q(patient__patient_id__icontains=query)
        )

    wb = Workbook()
    ws = wb.active
    ws.title = "Visit History"

    # Header row
    headers = [
        _('Date'), _('Patient ID'), _('Patient Name'), _('Department'), _('Doctor'), _('Diagnosis'), _('Status')
    ]
    
    header_fill = PatternFill(start_color='5D2D91', end_color='5D2D91', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True)

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=str(header))
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')

    # Data
    for row_num, visit in enumerate(visits[:1000], 2):
        ws.cell(row=row_num, column=1, value=visit.visit_date.strftime('%Y-%m-%d %H:%M'))
        ws.cell(row=row_num, column=2, value=visit.patient.patient_id)
        ws.cell(row=row_num, column=3, value=visit.patient.full_name)
        ws.cell(row=row_num, column=4, value=visit.current_room.name if visit.current_room else "-")
        ws.cell(row=row_num, column=5, value=visit.doctor.get_full_name() if visit.doctor else "-")
        diag_str = f"{visit.diagnosis.code} - {visit.diagnosis.name}" if visit.diagnosis else "-"
        ws.cell(row=row_num, column=6, value=diag_str)
        ws.cell(row=row_num, column=7, value=str(visit.get_status_display()))

    # Column width
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 30
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 25
    ws.column_dimensions['F'].width = 40
    ws.column_dimensions['G'].width = 15

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"Visit_History_{timezone.now().strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response

@login_required
@permission_required('medical_records.view_visit', raise_exception=True)
def visit_summary_pdf(request, visit_uuid):
    """Generate PDF summary for a single visit."""
    visit = get_object_or_404(
        Visit.objects.visible_to(request.user).select_related(
            'patient', 'doctor', 'checked_in_by', 'triage_nurse', 'current_room', 'diagnosis'
        ).prefetch_related(
            'logs__performed_by', 
            'logs__room',
            'secondary_diagnoses'
        ),
        uuid=visit_uuid
    )
    enrich_visit_lab_results(visit)
    from clinic_core.pdf_utils import render_to_pdf
    context = {'visit': visit}
    pdf = render_to_pdf('medical_records/pdf/visit_summary_pdf.html', context)
    if pdf:
        pdf['Content-Disposition'] = f'inline; filename="Visit_{visit.patient.patient_id}_{visit.visit_date.date()}.pdf"'
        return pdf
    from django.http import HttpResponse
    return HttpResponse("Error generating PDF", status=500)

@login_required
def search_diagnosis_ajax(request):
    """AJAX endpoint for Select2 diagnosis search."""
    from django.http import JsonResponse
    from django.db.models import Q
    
    query = request.GET.get('q', '')
    try:
        page = int(request.GET.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    page_size = 30
    
    start = (page - 1) * page_size
    end = start + page_size
    
    queryset = Diagnosis.objects.all()
    if query:
        queryset = queryset.filter(
            Q(code__icontains=query) | Q(name__icontains=query)
        )
    
    total_count = queryset.count()
    results = queryset.order_by('code')[start:end]
    
    data = {
        'results': [{'id': d.id, 'text': f"{d.code} - {d.name}"} for d in results],
        'total_count': total_count
    }
    return JsonResponse(data)


@login_required
@permission_required('medical_records.view_menu_specialist_nutrition', raise_exception=True)
def nutrition_statistics(request):
    """
    Halaman statistika nutrisi format TLHIS/04 untuk laporan ke Ministerio da Saúde.
    Data yang tersedia: MUAC, registrasi pasien, pasien baru.
    Data yang belum ada (—): tinggi badan, Z-score, suplemen, PTE/PTI.
    """
    from dateutil.relativedelta import relativedelta
    from django.db.models import Count, Q
    from patients.models import Patient

    # --- Filter Bulan ---
    selected_month = request.GET.get('month', timezone.localdate().strftime('%Y-%m'))
    try:
        year, month = int(selected_month[:4]), int(selected_month[5:7])
    except (ValueError, IndexError):
        year, month = timezone.localdate().year, timezone.localdate().month

    month_start = timezone.datetime(year, month, 1).date()
    if month == 12:
        month_end = timezone.datetime(year + 1, 1, 1).date()
    else:
        month_end = timezone.datetime(year, month + 1, 1).date()

    today = timezone.localdate()

    # --- Batas usia ---
    limit_0m  = today - relativedelta(months=0)
    limit_24m = today - relativedelta(months=24)
    limit_59m = today - relativedelta(months=59)

    # Pasien anak berdasarkan kelompok usia
    def children_qs(age_min_m, age_max_m, gender=None):
        dob_upper = today - relativedelta(months=age_min_m)
        dob_lower = today - relativedelta(months=age_max_m)
        qs = Patient.objects.filter(
            date_of_birth__lte=dob_upper,
            date_of_birth__gt=dob_lower,
        )
        if gender:
            qs = qs.filter(gender=gender)
        return qs

    # Kunjungan NUTRISI pada bulan ini
    nutri_visits_month = Visit.objects.filter(
        current_room__code='NUTRISI',
        visit_date__date__gte=month_start,
        visit_date__date__lt=month_end,
    )

    def count_visits(age_min_m, age_max_m, gender, qs=None):
        if qs is None:
            qs = nutri_visits_month
        dob_upper = today - relativedelta(months=age_min_m)
        dob_lower = today - relativedelta(months=age_max_m)
        return qs.filter(
            patient__date_of_birth__lte=dob_upper,
            patient__date_of_birth__gt=dob_lower,
            patient__gender=gender,
        ).values('patient').distinct().count()

    def count_new_visits(age_min_m, age_max_m, gender):
        dob_upper = today - relativedelta(months=age_min_m)
        dob_lower = today - relativedelta(months=age_max_m)
        return nutri_visits_month.filter(
            patient__date_of_birth__lte=dob_upper,
            patient__date_of_birth__gt=dob_lower,
            patient__gender=gender,
            patient_type='FOUN',
        ).values('patient').distinct().count()

    # MUAC classification — only for visits with MUAC recorded
    def count_muac(gender, muac_min=None, muac_max=None):
        qs = nutri_visits_month.filter(
            patient__date_of_birth__lte=today - relativedelta(months=6),
            patient__date_of_birth__gt=today - relativedelta(months=59),
            patient__gender=gender,
            muac__isnull=False,
        )
        if muac_min is not None:
            qs = qs.filter(muac__gte=muac_min)
        if muac_max is not None:
            qs = qs.filter(muac__lt=muac_max)
        return qs.count()

    s = {
        # --- Registrasi (1-3) ---
        'reg_0_23_m':  count_visits(0, 23, 'M'),
        'reg_0_23_f':  count_visits(0, 23, 'F'),
        'reg_24_59_m': count_visits(24, 59, 'M'),
        'reg_24_59_f': count_visits(24, 59, 'F'),

        'new_0_23_m':  count_new_visits(0, 23, 'M'),
        'new_0_23_f':  count_new_visits(0, 23, 'F'),
        'new_24_59_m': count_new_visits(24, 59, 'M'),
        'new_24_59_f': count_new_visits(24, 59, 'F'),

        'mon_0_23_m':  count_visits(0, 23, 'M'),
        'mon_0_23_f':  count_visits(0, 23, 'F'),
        'mon_24_59_m': count_visits(24, 59, 'M'),
        'mon_24_59_f': count_visits(24, 59, 'F'),

        # --- WAZ / WHZ / HAZ — belum ada data (None = tampil "—") ---
        'waz_norm_0_23_m': None, 'waz_norm_0_23_f': None,
        'waz_norm_24_59_m': None, 'waz_norm_24_59_f': None,
        'waz_mod_0_23_m': None, 'waz_mod_0_23_f': None,
        'waz_mod_24_59_m': None, 'waz_mod_24_59_f': None,
        'waz_sev_0_23_m': None, 'waz_sev_0_23_f': None,
        'waz_sev_24_59_m': None, 'waz_sev_24_59_f': None,

        'whz_norm_0_23_m': None, 'whz_norm_0_23_f': None,
        'whz_norm_24_59_m': None, 'whz_norm_24_59_f': None,
        'whz_mod_0_23_m': None, 'whz_mod_0_23_f': None,
        'whz_mod_24_59_m': None, 'whz_mod_24_59_f': None,
        'whz_sev_0_23_m': None, 'whz_sev_0_23_f': None,
        'whz_sev_24_59_m': None, 'whz_sev_24_59_f': None,
        'whz_ow_0_23_m': None, 'whz_ow_0_23_f': None,
        'whz_ow_24_59_m': None, 'whz_ow_24_59_f': None,
        'whz_ob_0_23_m': None, 'whz_ob_0_23_f': None,
        'whz_ob_24_59_m': None, 'whz_ob_24_59_f': None,

        'haz_norm_0_23_m': None, 'haz_norm_0_23_f': None,
        'haz_norm_24_59_m': None, 'haz_norm_24_59_f': None,
        'haz_mod_0_23_m': None, 'haz_mod_0_23_f': None,
        'haz_mod_24_59_m': None, 'haz_mod_24_59_f': None,
        'haz_sev_0_23_m': None, 'haz_sev_0_23_f': None,
        'haz_sev_24_59_m': None, 'haz_sev_24_59_f': None,

        # --- Konseling (7) ---
        'counsel_0_23_m': None, 'counsel_0_23_f': None,
        'counsel_24_59_m': None, 'counsel_24_59_f': None,

        # --- MUAC (8) — DATA TERSEDIA ---
        'muac_norm_m': count_muac('M', muac_min=12.5),
        'muac_norm_f': count_muac('F', muac_min=12.5),
        'muac_mam_m':  count_muac('M', muac_min=11.5, muac_max=12.5),
        'muac_mam_f':  count_muac('F', muac_min=11.5, muac_max=12.5),
        'muac_sam_m':  count_muac('M', muac_max=11.5),
        'muac_sam_f':  count_muac('F', muac_max=11.5),

        # --- PTE / PTI / Suplemen — belum ada ---
        'pte_cured_m': None, 'pte_cured_f': None,
        'pte_not_cured_m': None, 'pte_not_cured_f': None,
        'pte_default_m': None, 'pte_default_f': None,
        'pte_dead_m': None, 'pte_dead_f': None,
        'pti_m': None, 'pti_f': None,
        'vita_6_11_m': None, 'vita_6_11_f': None,
        'vita_12_59_m': None, 'vita_12_59_f': None,
        'alumb_12_23_m': None, 'alumb_12_23_f': None,
        'alumb_24_59_m': None, 'alumb_24_59_f': None,
        'mnr_6_23_m': None, 'mnr_6_23_f': None,
    }

    return render(request, 'medical_records/nutrition_statistics.html', {
        'selected_month': selected_month,
        's': s,
        'missing_fields': True,
    })
