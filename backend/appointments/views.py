from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from django.utils import timezone
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView
from django.db.models import Q

from .models import Appointment
from .forms import AppointmentForm


@login_required
def appointment_calendar(request):
    date_str = request.GET.get('date', '')
    if date_str:
        try:
            from datetime import datetime
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            filter_date = timezone.localdate()
    else:
        filter_date = timezone.localdate()

    appointments = Appointment.objects.visible_to(request.user).filter(
        appointment_date=filter_date
    ).select_related('patient', 'department', 'doctor').order_by('appointment_time')

    upcoming = Appointment.objects.visible_to(request.user).filter(
        appointment_date__gte=timezone.localdate(),
        status__in=['SCHEDULED', 'CONFIRMED']
    ).select_related('patient', 'department', 'doctor').order_by('appointment_date', 'appointment_time')[:20]

    today_count = Appointment.objects.visible_to(request.user).filter(appointment_date=timezone.localdate()).count()
    scheduled_count = Appointment.objects.visible_to(request.user).filter(status='SCHEDULED', appointment_date__gte=timezone.localdate()).count()

    return render(request, 'appointments/calendar.html', {
        'appointments': appointments,
        'upcoming': upcoming,
        'filter_date': filter_date,
        'today_count': today_count,
        'scheduled_count': scheduled_count,
    })


@login_required
def appointment_create(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.created_by = request.user
            appointment.save()
            messages.success(request, _("Appointment created successfully."))
            return redirect('appointment_calendar')
    else:
        patient_uuid = request.GET.get('patient')
        initial = {}
        if patient_uuid:
            from patients.models import Patient
            try:
                patient = Patient.objects.visible_to(request.user).get(uuid=patient_uuid)
                initial['patient'] = patient
            except (Patient.DoesNotExist, ValueError):
                pass
        form = AppointmentForm(initial=initial)

    return render(request, 'appointments/form.html', {
        'form': form,
        'title': _('Create Appointment'),
    })


@login_required
def appointment_edit(request, uuid):
    appointment = get_object_or_404(Appointment.objects.visible_to(request.user), uuid=uuid)

    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, _("Appointment updated successfully."))
            return redirect('appointment_calendar')
    else:
        form = AppointmentForm(instance=appointment)

    return render(request, 'appointments/form.html', {
        'form': form,
        'title': _('Edit Appointment'),
        'appointment': appointment,
    })


@login_required
def appointment_cancel(request, uuid):
    appointment = get_object_or_404(Appointment.objects.visible_to(request.user), uuid=uuid)

    if request.method == 'POST':
        appointment.status = 'CANCELLED'
        appointment.cancelled_reason = request.POST.get('cancelled_reason', '')
        appointment.save()
        messages.success(request, _("Appointment cancelled."))
        return redirect('appointment_calendar')

    return render(request, 'appointments/cancel.html', {
        'appointment': appointment,
    })


@login_required
def appointment_status_update(request, uuid):
    appointment = get_object_or_404(Appointment.objects.visible_to(request.user), uuid=uuid)
    new_status = request.POST.get('status')

    valid_statuses = dict(Appointment.STATUS_CHOICES).keys()
    if new_status in valid_statuses:
        appointment.status = new_status
        appointment.save()
        messages.success(request, _("Appointment status updated to %(status)s.") % {'status': appointment.get_status_display()})

    return redirect('appointment_calendar')


@login_required
def appointment_check_in_visit(request, uuid):
    """
    Automates the transition from Appointment to Visit.
    Marks Appointment as CHECKED_IN and creates a new Visit record in the Triage queue.
    """
    appointment = get_object_or_404(Appointment.objects.visible_to(request.user), uuid=uuid)

    # 1. Update Appointment Status
    appointment.status = 'CHECKED_IN'
    appointment.save()

    # 2. Prepare Visit Creation Data
    from patients.models import DailyQueue
    from medical_records.models import Visit, Room
    from medical_records.utils import log_visit_action

    today = timezone.localdate()

    # Get or create today's queue
    queue, created = DailyQueue.objects.get_or_create(date=today, department='General')
    queue_number = queue.get_next_number()

    # Get Triage Room (consistency with patients/views.py)
    triage_room = Room.objects.filter(code='TRIAGE').first() or Room.objects.filter(code='ROOM_2').first()

    # 3. Create Visit
    visit = Visit.objects.create(
        patient=appointment.patient,
        queue_number=queue_number,
        status='SCH',
        current_room=triage_room,
        visit_fee=0.00,  # Default to free follow-up
        patient_type='TUAN',
        checked_in_by=request.user,
    )

    log_visit_action(visit, 'CHECK_IN', request.user, room=triage_room)

    messages.success(request, _("Check-in successful! Patient %(name)s is now in the Triage queue (#%(num)s).") % {
        'name': appointment.patient.full_name,
        'num': queue_number
    })

    return redirect('queue_ticket', visit_uuid=visit.uuid)


@login_required
def hiv_appointment_calendar(request):
    """
    Dedicated appointment calendar for HIV/AIDS patients.
    Only accessible by HIV staff and superusers.
    Shows ONLY HIV patient appointments — completely isolated from the general queue.
    """
    # Security: only HIV staff or superuser may access
    is_hiv_staff = False
    if request.user.is_superuser:
        is_hiv_staff = True
    else:
        staff_profile = getattr(request.user, 'staff_profile', None)
        if staff_profile:
            try:
                dept_code = staff_profile.department.code.upper()
                is_hiv_staff = dept_code in ['HIV', 'AIDS']
            except AttributeError:
                pass

    if not is_hiv_staff:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    date_str = request.GET.get('date', '')
    if date_str:
        try:
            from datetime import datetime
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            filter_date = timezone.localdate()
    else:
        filter_date = timezone.localdate()

    # Only HIV patient appointments
    appointments = Appointment.objects.filter(
        patient__is_hiv_patient=True,
        appointment_date=filter_date
    ).select_related('patient', 'department', 'doctor').order_by('appointment_time')

    upcoming = Appointment.objects.filter(
        patient__is_hiv_patient=True,
        appointment_date__gte=timezone.localdate(),
        status__in=['SCHEDULED', 'CONFIRMED']
    ).select_related('patient', 'department', 'doctor').order_by('appointment_date', 'appointment_time')[:20]

    today_count = Appointment.objects.filter(
        patient__is_hiv_patient=True,
        appointment_date=timezone.localdate()
    ).count()

    scheduled_count = Appointment.objects.filter(
        patient__is_hiv_patient=True,
        status='SCHEDULED',
        appointment_date__gte=timezone.localdate()
    ).count()

    return render(request, 'appointments/hiv_calendar.html', {
        'appointments': appointments,
        'upcoming': upcoming,
        'filter_date': filter_date,
        'today_count': today_count,
        'scheduled_count': scheduled_count,
    })
