import os
import subprocess
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

import shutil
import tempfile
from .models import AuditLog

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
