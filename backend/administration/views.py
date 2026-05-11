import os
import subprocess
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

import shutil
import tempfile
from .models import AuditLog
from patients.models import Patient, Municipio, PostoAdministrativo, Suco, Aldeia
from medical_records.models import Visit, Diagnosis
from django.db.models import Count, Q, F

def get_pg_bin(command):
    path = shutil.which(command)
    if path:
        return path
    if os.name == 'nt':
        base_dir = r"C:\Program Files\PostgreSQL"
        if os.path.exists(base_dir):
            for version in ['18', '17', '16', '15', '14', '13', '12']:
                candidate = os.path.join(base_dir, version, 'bin', f"{command}.exe")
                if os.path.exists(candidate):
                    return candidate
    return command

def is_admin(user):
    return user.is_active and (user.is_superuser or user.groups.filter(name='Admin').exists())

@user_passes_test(is_admin)
def backup_restore_view(request):
    return render(request, 'administration/backup_restore.html')

@user_passes_test(is_admin)
def backup_database(request):
    db_conf = settings.DATABASES['default']
    db_name = db_conf['NAME']
    db_user = db_conf['USER']
    db_password = db_conf['PASSWORD']
    db_host = db_conf['HOST']
    db_port = db_conf['PORT']

    # Filename with timestamp
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    filename = f"backup_{db_name}_{timestamp}.sql"

    # Command to run pg_dump
    # Note: Using --clean to include DROP commands for easier restoration
    pg_dump_path = get_pg_bin('pg_dump')
    cmd = [
        pg_dump_path,
        '-h', db_host,
        '-p', str(db_port),
        '-U', db_user,
        '--clean',
        '--if-exists',
        '--format=p', # Plain text SQL
        db_name
    ]

    env = os.environ.copy()
    env['PGPASSWORD'] = db_password

    try:
        result = subprocess.run(cmd, env=env, capture_output=True)
        
        if result.returncode != 0:
            error_msg = result.stderr.decode('utf-8', errors='replace')
            messages.error(request, _(f"Backup failed: {error_msg}"))
            return redirect('backup_restore')
        
        response = HttpResponse(result.stdout, content_type='application/sql')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        messages.error(request, _(f"Backup failed: {str(e)}"))
        return redirect('backup_restore')

@user_passes_test(is_admin)
def restore_database(request):
    if request.method == 'POST' and request.FILES.get('backup_file'):
        backup_file = request.FILES['backup_file']
        
        # Security: Check file extension
        if not backup_file.name.endswith('.sql'):
            messages.error(request, _("Invalid file format. Only .sql files are allowed."))
            return redirect('backup_restore')

        # Use tempfile to avoid fixed-path collisions and security issues
        with tempfile.NamedTemporaryFile(delete=False, suffix='.sql') as tmp_file:
            for chunk in backup_file.chunks():
                tmp_file.write(chunk)
            temp_path = tmp_file.name

        db_conf = settings.DATABASES['default']
        db_name = db_conf['NAME']
        db_user = db_conf['USER']
        db_password = db_conf['PASSWORD']
        db_host = db_conf['HOST']
        db_port = db_conf['PORT']

        # Restore using psql
        psql_path = get_pg_bin('psql')
        cmd = [
            psql_path,
            '-h', db_host,
            '-p', str(db_port),
            '-U', db_user,
            '-d', db_name,
            '-f', temp_path
        ]

        env = os.environ.copy()
        env['PGPASSWORD'] = db_password

        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.returncode == 0:
                messages.success(request, _("Database restored successfully!"))
                # Log the critical action
                AuditLog.objects.create(
                    user=request.user,
                    action='UPDATE',
                    module='ADMIN',
                    object_repr=f"Database restored from {backup_file.name}",
                    ip_address=get_client_ip(request)
                )
            else:
                messages.error(request, _(f"Restore failed: {result.stderr}"))
        except Exception as e:
            messages.error(request, _(f"An error occurred during restore: {str(e)}"))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    else:
        messages.warning(request, _("Please select a valid backup file."))

    return redirect('backup_restore')

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@user_passes_test(is_admin)
def geographical_dashboard(request):
    """Management dashboard for tracking patients and diseases by location."""
    municipio_id = request.GET.get('municipio')
    posto_id = request.GET.get('posto')
    suco_id = request.GET.get('suco')
    
    # Base Querysets
    patients = Patient.objects.all()
    visits = Visit.objects.filter(status='COM', visit_diagnoses__isnull=False).distinct()

    # Filtering Logic
    current_level = 'Município'
    filter_label = _("All Timor-Leste")
    
    if suco_id:
        suco = get_object_or_404(Suco, pk=suco_id)
        patients = patients.filter(suco=suco)
        visits = visits.filter(patient__suco=suco)
        location_group = 'aldeia__name'
        current_level = 'Aldeia'
        filter_label = suco.name
    elif posto_id:
        posto = get_object_or_404(PostoAdministrativo, pk=posto_id)
        patients = patients.filter(posto_administrativo=posto)
        visits = visits.filter(patient__posto_administrativo=posto)
        location_group = 'suco__name'
        current_level = 'Suco'
        filter_label = posto.name
    elif municipio_id:
        municipio = get_object_or_404(Municipio, pk=municipio_id)
        patients = patients.filter(municipio=municipio)
        visits = visits.filter(patient__municipio=municipio)
        location_group = 'posto_administrativo__name'
        current_level = 'Posto'
        filter_label = municipio.name
    else:
        location_group = 'municipio__name'
        current_level = 'Município'
        filter_label = _("All Timor-Leste")

    # 1. Patient Distribution Stats
    # Optimized: Values first, then annotate
    geo_stats = patients.values(location_name=F(location_group)).annotate(
        total=Count('pk')
    ).order_by('-total')[:15]

    # 2. Top Diseases Stats
    disease_stats = visits.values(
        'visit_diagnoses__diagnosis__name', 'visit_diagnoses__diagnosis__code'
    ).annotate(
        total=Count('pk')
    ).order_by('-total')[:10]

    # 3. Monthly Trend (Last 6 Months)
    # Filter by date first to reduce the working set
    six_months_ago = timezone.now() - timezone.timedelta(days=180)
    trend_stats = visits.filter(visit_date__gte=six_months_ago).values(
        'visit_date__year', 'visit_date__month'
    ).annotate(
        total=Count('pk')
    ).order_by('visit_date__year', 'visit_date__month')

    # Data for Selects
    municipios = Municipio.objects.all()
    postos = PostoAdministrativo.objects.filter(municipio_id=municipio_id) if municipio_id else []
    sucos = Suco.objects.filter(posto_id=posto_id) if posto_id else []

    return render(request, 'administration/geo_dashboard.html', {
        'geo_stats': geo_stats,
        'disease_stats': disease_stats,
        'trend_stats': trend_stats,
        'municipios': municipios,
        'postos': postos,
        'sucos': sucos,
        'current_municipio': municipio_id,
        'current_posto': posto_id,
        'current_suco': suco_id,
        'current_level': current_level,
        'filter_label': filter_label,
        'location_group_field': location_group,
    })
