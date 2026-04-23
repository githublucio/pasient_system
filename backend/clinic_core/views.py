from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Sum, Q, F
from decimal import Decimal


def csrf_failure(request, reason=""):
    return render(request, '403_csrf.html', status=403)


@login_required
def main_dashboard(request):
    # 1. Role-based Redirection
    if not request.user.is_superuser and not request.user.groups.filter(name__in=['Admin', 'Superadmin']).exists():
        if hasattr(request.user, 'staff_profile'):
            return redirect(request.user.staff_profile.home_url)

    from patients.models import Patient
    from medical_records.models import Visit, Diagnosis
    from billing.models import Invoice

    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))

    # --- Patient stats (Separated) ---
    total_patients = Patient.objects.count()
    total_patients_hiv = Patient.objects.filter(is_hiv_patient=True).count()
    total_patients_general = total_patients - total_patients_hiv

    # New registered today
    patients_today = Patient.objects.filter(created_at__date=today).count()
    patients_today_hiv = Patient.objects.filter(created_at__date=today, is_hiv_patient=True).count()
    patients_today_gen = patients_today - patients_today_hiv

    # --- Visit stats (Separated) ---
    all_visits_today = Visit.objects.filter(visit_date__date=today)
    
    # General
    visits_today_gen = all_visits_today.filter(patient__is_hiv_patient=False).count()
    visits_ip_gen = all_visits_today.filter(status__in=['SCH', 'IP'], patient__is_hiv_patient=False).count()
    visits_com_gen = all_visits_today.filter(status='COM', patient__is_hiv_patient=False).count()
    
    # HIV
    visits_today_hiv = all_visits_today.filter(patient__is_hiv_patient=True).count()
    visits_ip_hiv = all_visits_today.filter(status__in=['SCH', 'IP'], patient__is_hiv_patient=True).count()
    visits_com_hiv = all_visits_today.filter(status='COM', patient__is_hiv_patient=True).count()

    # Top 10 diagnoses (General only for main dashboard)
    top_diagnoses = Visit.objects.filter(
        visit_date__year=year,
        diagnosis__isnull=False,
        patient__is_hiv_patient=False
    ).values(
        diag_code=F('diagnosis__code'),
        diag_name=F('diagnosis__name'),
    ).annotate(
        total=Count('uuid')
    ).order_by('-total')[:10]

    # Monthly visit trend (General vs HIV)
    monthly_visits = []
    for m in range(1, 13):
        count_gen = Visit.objects.filter(visit_date__year=year, visit_date__month=m, patient__is_hiv_patient=False).count()
        count_hiv = Visit.objects.filter(visit_date__year=year, visit_date__month=m, patient__is_hiv_patient=True).count()
        monthly_visits.append({'month': m, 'count': count_gen, 'count_hiv': count_hiv})

    # Billing stats for the year
    billing_year = Invoice.objects.filter(
        created_at__year=year
    ).exclude(status='CANCELLED').aggregate(
        total_billed=Sum('total_amount'),
        total_paid=Sum('amount_paid'),
        count=Count('uuid'),
    )
    billing_today = Invoice.objects.filter(
        created_at__date=today
    ).exclude(status='CANCELLED').aggregate(
        total_billed=Sum('total_amount'),
        total_paid=Sum('amount_paid'),
    )

    # Gender breakdown
    gender_stats = Patient.objects.filter(
        created_at__year=year
    ).values('gender').annotate(total=Count('uuid')).order_by('-total')

    # Available years for filter
    first_patient = Patient.objects.order_by('created_at').first()
    start_year = first_patient.created_at.year if first_patient else today.year
    available_years = list(range(start_year, today.year + 1))

    return render(request, 'dashboard.html', {
        'today': today,
        'year': year,
        'available_years': available_years,
        # Patient
        'total_patients': total_patients,
        'total_patients_hiv': total_patients_hiv,
        'total_patients_gen': total_patients_general,
        'patients_today_gen': patients_today_gen,
        'patients_today_hiv': patients_today_hiv,
        # Visits General
        'visits_today_gen': visits_today_gen,
        'visits_ip_gen': visits_ip_gen,
        'visits_com_gen': visits_com_gen,
        # Visits HIV
        'visits_today_hiv': visits_today_hiv,
        'visits_ip_hiv': visits_ip_hiv,
        'visits_com_hiv': visits_com_hiv,
        # Diagnosis
        'top_diagnoses': top_diagnoses,
        # Monthly
        'monthly_visits': monthly_visits,
        # Billing
        'billing_year_billed': billing_year['total_billed'] or Decimal('0.00'),
        'billing_year_paid': billing_year['total_paid'] or Decimal('0.00'),
        'billing_year_count': billing_year['count'] or 0,
        'billing_today_billed': billing_today['total_billed'] or Decimal('0.00'),
        'billing_today_paid': billing_today['total_paid'] or Decimal('0.00'),
        # Gender
        'gender_stats': gender_stats,
    })
