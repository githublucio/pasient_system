# Security, Staff, Administration & Infrastructure Audit Report

**Project**: Clinic Bairo Pite Lanud – Patient Management System  
**Audit Date**: 2026-04-12  
**Scope**: Security, Staff management, Administration, RBAC, Middleware, Encryption, Templates, Printing  
**Codebase Location**: `D:\pasient_system\backend`

---

## Executive Summary

The Clinic Management System is a Django 5.2 application with PostgreSQL backend serving a healthcare facility in East Timor. The system includes patient management, medical records, billing, laboratory, pharmacy, radiology, pathology, printing, staff management, and administration modules. Overall, the system has a solid foundation with proper RBAC, audit logging, and encryption, but has **several critical and high-severity security issues** that must be addressed before production deployment.

---

## 1. RBAC (Role-Based Access Control)

### ✅ What's Implemented
- **Django Groups as Roles**: Roles (Groups) CRUD via `RoleListView`, `RoleCreateView`, `RoleUpdateView`, `RoleDeleteView`
- **Permission Matrix**: Full permission matrix UI (`RolePermissionMatrixView`) covering all modules with View/Add/Change/Delete + custom permissions
- **User-Role Assignment**: `UserRoleMapperView` allows assigning multiple roles per user via a modal UI
- **Custom Permissions**: Defined on `StaffProfile` model: `can_export_staff`, `view_menu_staff`, `view_menu_master_data`; and referenced across modules (patients, medical_records, billing, etc.)
- **Sidebar Menu Gating**: `base.html` uses Django `{% if perms.* %}` checks to conditionally show menu sections
- **View-level Protection**: All staff views use `LoginRequiredMixin` + `PermissionRequiredMixin`
- **Signal-based Auto-grouping**: `signals.py` auto-assigns Django Groups based on `StaffCategory` name (Doctor, Nurse, Pharmacist, Admin, Receptionist)
- **Staff Registration with Roles**: `IntegratedStaffForm` includes role assignment checkboxes during staff creation

### ⚠️ Issues Found

| # | Severity | Issue | Details |
|---|----------|-------|---------|
| 1 | **HIGH** | `RolePermissionMatrixView.get()` lacks `PermissionRequiredMixin` | The GET view only uses `LoginRequiredMixin`. Any authenticated user can view the permission matrix. Only the POST for `UserRoleMapperView` requires `auth.change_user`. The `RolePermissionMatrixView` should require a permission like `auth.change_group`. |
| 2 | **MEDIUM** | Permission collision risk in matrix POST | `Permission.objects.filter(codename__in=selected_perms)` matches by codename only, not by `content_type`. If two apps define the same codename (e.g., `view_room`), the wrong permissions could be assigned. Should filter by both `codename` and `content_type__app_label`. |
| 3 | **MEDIUM** | Signal auto-grouping conflicts with manual assignment | `sync_user_groups` signal adds groups on every `StaffProfile` save, potentially re-adding groups a user was intentionally removed from. Uses `user.groups.add()` which is additive but could conflict with admin intentions. |
| 4 | **LOW** | Admin users auto-granted `is_staff=True` | Signal sets `is_staff=True` for Admin-category staff, granting Django admin panel access. This is by design but should be documented and verified against intended policy. |
| 5 | **LOW** | No password strength enforcement in `IntegratedStaffForm` | The form uses `forms.CharField(widget=forms.PasswordInput())` and calls `User.objects.create_user()` but doesn't run Django's password validators (`AUTH_PASSWORD_VALIDATORS`). Weak passwords can be set. |

### Recommendations
- Add `PermissionRequiredMixin` with `permission_required = 'auth.change_group'` to `RolePermissionMatrixView`
- Filter permissions by `content_type__app_label` + `codename` in the matrix POST handler
- Add `validate_password()` call in `IntegratedStaffForm.save()` before creating the user
- Consider adding a "password change" feature to `StaffUpdateForm`

---

## 2. Middleware & Audit Logging

### ✅ What's Implemented
- **AuditLogMiddleware**: Registered in `MIDDLEWARE` list
- **Login/Logout Logging**: Django signals `user_logged_in` and `user_logged_out` create `AuditLog` entries with IP address
- **AuditLog Model**: Comprehensive model with `timestamp`, `user`, `action`, `module`, `model_name`, `object_id`, `object_repr`, `ip_address`, `changes` (JSONField for diffs)
- **Proper Indexes**: Three indexes on AuditLog for efficient querying (timestamp, user+timestamp, module+timestamp)
- **Database Restore Audit**: Restore operations are logged in `AuditLog`
- **IP Extraction**: `get_client_ip()` handles `X-Forwarded-For` header

### ⚠️ Issues Found

| # | Severity | Issue | Details |
|---|----------|-------|---------|
| 1 | **CRITICAL** | AuditLogMiddleware is essentially a no-op | The middleware `__call__` method only passes the request through. It does NOT log CREATE, UPDATE, DELETE operations on models. Only LOGIN/LOGOUT are logged via signals. The `security_protocol.md` requires "Every request to the system must be logged." |
| 2 | **HIGH** | No audit logging for data changes (CRUD) | There are no signals or hooks to log when patient records, medical records, billing, prescriptions, etc. are created, updated, or deleted. This is a compliance violation per the security protocol. |
| 3 | **HIGH** | No audit log viewer in the UI | There is no view/template for administrators to browse, filter, or export audit logs. The data is stored but inaccessible without Django admin. |
| 4 | **MEDIUM** | `DefaultTetumMiddleware` is defined but not registered | The `DefaultTetumMiddleware` class exists in `middleware.py` but is NOT included in the `MIDDLEWARE` list in `settings.py`. Dead code. |
| 5 | **MEDIUM** | IP spoofing via X-Forwarded-For | `get_client_ip()` trusts `HTTP_X_FORWARDED_FOR` without validation. An attacker can set this header to any value. Should use a trusted proxy list or Django's `SECURE_PROXY_SSL_HEADER`. |

### Recommendations
- Implement model-level audit logging using `django-auditlog` library or custom `post_save`/`post_delete` signals for all critical models
- Create an audit log viewer (list view with filters by user, date range, module, action)
- Remove or register `DefaultTetumMiddleware`
- Add IP validation / trusted proxy configuration

---

## 3. Admin Panel Configuration

### ✅ What's Implemented
- `django.contrib.admin` is in `INSTALLED_APPS`
- Admin URL at `/admin/`
- Admin is linked in sidebar for superusers
- Master data (Lab Tests, Pathology Tests) are managed through admin

### ⚠️ Issues Found

| # | Severity | Issue | Details |
|---|----------|-------|---------|
| 1 | **HIGH** | No models registered in admin | Both `staff/admin.py` and `administration/admin.py` contain only `# Register your models here.` - no models are registered. `StaffProfile`, `Department`, `StaffCategory`, `Position`, `AuditLog` are all unregistered. |
| 2 | **MEDIUM** | Admin relies on hardcoded sidebar URLs | `base.html` links to `/admin/laboratory/labtest/` and `/admin/pathology/pathologytest/` via hardcoded URLs. These will only work if those models are registered in admin (which needs verification). |
| 3 | **LOW** | No custom admin site title or branding | The Django admin uses default branding. Should be customized for the clinic. |

### Recommendations
- Register all models in their respective `admin.py` files with appropriate `ModelAdmin` classes
- Register `AuditLog` as read-only in admin
- Set `admin.site.site_header`, `admin.site.site_title`, `admin.site.index_title`

---

## 4. Session Management

### ✅ What's Implemented
- `SESSION_EXPIRE_AT_BROWSER_CLOSE = True` – session dies when browser closes
- `SESSION_COOKIE_AGE = 28800` (8 hours max)
- `SESSION_COOKIE_SECURE` configurable via environment variable
- Login/Logout redirects properly configured
- Custom logout supports GET for convenience

### ⚠️ Issues Found

| # | Severity | Issue | Details |
|---|----------|-------|---------|
| 1 | **HIGH** | Session timeout violates security protocol | `security_protocol.md` requires "Maximum 15 minutes of inactivity" but `SESSION_COOKIE_AGE = 28800` (8 hours). There is no inactivity-based timeout. |
| 2 | **HIGH** | `SESSION_COOKIE_SECURE = False` in production default | The `.env` has `DEBUG=True` and no `SESSION_COOKIE_SECURE` set, defaulting to `False`. Cookies will be sent over HTTP. |
| 3 | **HIGH** | Custom logout via GET is insecure | `custom_logout()` accepts GET requests (no CSRF check). An attacker can log out any user by tricking them into visiting `/accounts/logout/` or `/staff/logout/`. Should require POST with CSRF token. |
| 4 | **MEDIUM** | No `SESSION_COOKIE_HTTPONLY` setting | While Django defaults `SESSION_COOKIE_HTTPONLY=True`, it's not explicitly set, and should be documented. |
| 5 | **LOW** | Duplicate logout routes | Two logout URLs exist: `/accounts/logout/` (name='logout') and `/staff/logout/` (name='logout_custom'). This can cause confusion. |

### Recommendations
- Implement idle-timeout middleware (e.g., `django-session-timeout`) with 15-minute inactivity limit per security protocol
- Set `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, `SECURE_SSL_REDIRECT=True` in production
- Change `custom_logout` to require POST method only
- Remove duplicate logout route
- Add `SESSION_COOKIE_HTTPONLY = True` explicitly

---

## 5. CSRF & XSS Protection

### ✅ What's Implemented
- `CsrfViewMiddleware` is in MIDDLEWARE
- All forms use `{% csrf_token %}`
- Custom CSRF failure page (`403_csrf.html`) with user-friendly message
- `CSRF_FAILURE_VIEW = 'clinic_core.views.csrf_failure'`
- `CSRF_COOKIE_SECURE` configurable via env
- Django auto-escaping is active (default template engine behavior)
- `SECURE_BROWSER_XSS_FILTER = True`
- `SECURE_CONTENT_TYPE_NOSNIFF = True`
- `X_FRAME_OPTIONS = 'DENY'`

### ⚠️ Issues Found

| # | Severity | Issue | Details |
|---|----------|-------|---------|
| 1 | **HIGH** | `custom_logout` bypasses CSRF (GET method) | As noted above, the logout function doesn't check CSRF since it accepts GET. |
| 2 | **MEDIUM** | `backup_database` uses GET method | The backup download is triggered via GET form submission. While it's behind `@user_passes_test(is_admin)`, it should use POST for state-changing operations per REST conventions, and to prevent CSRF via image tags or link prefetching. |
| 3 | **MEDIUM** | No Content Security Policy (CSP) header | The application loads Bootstrap and fonts from CDNs (`cdn.jsdelivr.net`, `fonts.googleapis.com`) but has no CSP header. XSS attacks could inject scripts from any origin. |
| 4 | **LOW** | `SECURE_BROWSER_XSS_FILTER` is deprecated | Modern browsers have removed XSS auditor support. The `X-XSS-Protection` header is no longer effective. CSP is the proper replacement. |
| 5 | **MEDIUM** | No `SECURE_HSTS_SECONDS` configured | HTTP Strict Transport Security is not set. Should be configured for production. |

### Recommendations
- Add `django-csp` middleware with a strict Content Security Policy
- Set `SECURE_HSTS_SECONDS = 31536000` and `SECURE_HSTS_INCLUDE_SUBDOMAINS = True` for production
- Change backup to POST method
- Add `Referrer-Policy: strict-origin-when-cross-origin` header

---

## 6. Encryption (fields.py)

### ✅ What's Implemented
- `EncryptedTextField` using Fernet (AES-128-CBC) symmetric encryption
- Encryption key loaded from `ENCRYPTION_KEY` environment variable
- Transparent encrypt-on-save, decrypt-on-read
- Graceful fallback if decryption fails (returns raw value)

### ⚠️ Issues Found

| # | Severity | Issue | Details |
|---|----------|-------|---------|
| 1 | **CRITICAL** | Fallback generates a NEW random key if env var is missing | `if not key: key = Fernet.generate_key()` – If `ENCRYPTION_KEY` is unset during migrations or in any context, a random key is generated. Data encrypted with this key can NEVER be decrypted again. This is a data loss risk. Should raise an error instead. |
| 2 | **HIGH** | Encryption key is in `.env` file in plain text | `ENCRYPTION_KEY=CBZCl3WTjKwJwlgyXpFY8sWmQhutZK4bNyx0Ujjuj8I=` is stored in the `.env` file alongside the database password. If the repo is compromised, all encrypted data is exposed. |
| 3 | **HIGH** | `.env` file contains production credentials | `DB_PASSWORD=lanud2026` and `SECRET_KEY` are in `.env`. This file MUST be in `.gitignore` and MUST NOT be committed to version control. |
| 4 | **MEDIUM** | No key rotation mechanism | There is no way to rotate the encryption key without re-encrypting all existing data. |
| 5 | **MEDIUM** | `to_python` detection is fragile | `if isinstance(value, str) and not value.startswith('gAAAA')` – Fernet tokens start with `gAAAA` but this is an implementation detail that could change. The check is brittle. |
| 6 | **LOW** | Encrypted fields cannot be searched or indexed | By design, but important to note – any field using `EncryptedTextField` cannot participate in database queries (WHERE, ORDER BY, etc.). |

### Recommendations
- **Replace the fallback with `raise ImproperlyConfigured('ENCRYPTION_KEY must be set')`**
- Move encryption key to a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault)
- Ensure `.env` is in `.gitignore`
- Implement a key rotation management command
- Add a `deconstruct()` method so Django migrations work correctly

---

## 7. Base Template & Navigation

### ✅ What's Implemented
- **Professional sidebar layout**: Fixed sidebar (260px) with dark theme, responsive (hides on mobile with toggle)
- **Sticky topbar**: 60px with user dropdown (profile link, logout)
- **Permission-gated menu sections**: Each sidebar section checks Django permissions before rendering
- **Organized menu structure**: Dashboard, Patients, Medical, Lab, Other Services, Specialist Clinics, Billing, Inventory, HR, Master Data, System
- **Active link highlighting**: JavaScript auto-detects current path and adds `.active` class
- **Collapsible sub-menus**: System > Configuration uses toggle sub-menu
- **User profile dropdown**: Shows username, full name, profile link, logout with CSRF
- **Bootstrap 5.3**: Modern CSS framework with icons
- **Responsive design**: Mobile-friendly with sidebar toggle

### ⚠️ Issues Found

| # | Severity | Issue | Details |
|---|----------|-------|---------|
| 1 | **MEDIUM** | CDN dependency for Bootstrap | Loading Bootstrap CSS/JS from `cdn.jsdelivr.net` creates a single point of failure. If CDN is down, the entire UI breaks. Healthcare systems should use local static files. |
| 2 | **LOW** | Logo uses hardcoded path | `<img src="/media/Logo.png">` bypasses Django's `{% static %}` or `{{ MEDIA_URL }}` tags. |
| 3 | **LOW** | No footer | The template lacks a footer with version, copyright, or clinic info. |
| 4 | **LOW** | No breadcrumbs in base | Only `staff_list.html` includes breadcrumbs. Should be standardized in the base template. |
| 5 | **INFO** | No dark mode toggle | Minor UX enhancement that could reduce eye strain for medical staff working night shifts. |

### Assessment
The base template is **professional and well-structured**. The sidebar navigation is comprehensive and properly permission-gated. The responsive design works well. Overall quality: **Good**.

---

## 8. Dashboard

### ✅ What's Implemented
- **Year filter**: Dropdown to select year with auto-submit
- **Today summary cards**: Patients Today, Visits Today, Waiting/In Progress, Revenue Today
- **Year summary cards**: Total Patients (all time), Patients this year/month, Visits this year, Revenue this year (billed vs paid)
- **Monthly visit trend chart**: CSS-based bar chart (no JS library dependency)
- **Gender breakdown**: Male/Female/Other with icons
- **Top 10 diagnoses table**: ICD-10 code, name, case count, progress bar

### ⚠️ Issues Found

| # | Severity | Issue | Details |
|---|----------|-------|---------|
| 1 | **MEDIUM** | No permission check on dashboard | `main_dashboard` only uses `@login_required`. Any authenticated user (even with no permissions) can see all statistics including revenue figures. Should restrict financial data to billing/admin roles. |
| 2 | **MEDIUM** | Year parameter not validated | `year = int(request.GET.get('year', today.year))` – No validation. A malicious user could pass `year=99999999` causing expensive queries or `year=abc` causing a 500 error (ValueError). |
| 3 | **LOW** | No caching | Dashboard queries run on every page load. For 6000+ patients, this could be slow. Consider Django cache framework. |
| 4 | **LOW** | No appointments widget | The `appointments` app is installed but not represented on the dashboard. |

### Assessment
The dashboard is **comprehensive and well-designed** with relevant clinical KPIs. The CSS-only bar chart is clever. Overall quality: **Good**, but needs input validation and permission refinements.

---

## 9. Printing System (Patient Cards)

### ✅ What's Implemented
- **QR Code generation**: Using `qrcode` library, encodes `patient.patient_id`
- **Barcode generation**: Code128 using `python-barcode` library
- **CR80 card format**: Professional ID card layout matching standard card printer dimensions (85.6mm × 54mm)
- **Front side**: Logo, clinic name, patient ID (Orbitron font), full name, DOB, gender, address, QR code
- **Back side**: Mission statement, terms & conditions (in Tetum language), barcode
- **Print-optimized CSS**: `@media print` rules with exact dimensions, color preservation, page breaks
- **Lazy generation**: QR/barcode generated on first preview if missing, then cached on patient model
- **Google Fonts**: Orbitron for patient ID display

### ⚠️ Issues Found

| # | Severity | Issue | Details |
|---|----------|-------|---------|
| 1 | **HIGH** | No permission check on card preview/print | `preview_card` and `print_card_trigger` have NO `@login_required` or permission checks. Any anonymous user who knows a patient UUID can view patient data (name, DOB, address). This is a **HIPAA/PHI exposure**. |
| 2 | **MEDIUM** | `print_card_trigger` is a stub | Returns `HttpResponse("Signal sent to Printer")` – not actually connected to any printing backend. |
| 3 | **MEDIUM** | No validation of generated assets | `generate_patient_assets` doesn't verify the generated images are valid or handle failures gracefully. |
| 4 | **LOW** | Card template uses hardcoded background paths | `'/media/carad_bacgroun.jpeg'` and `'/media/Logo.png'` are hardcoded. |
| 5 | **LOW** | Google Fonts CDN dependency in print template | `fonts.googleapis.com` loaded for Orbitron font. If offline, card layout degrades. |

### Assessment
The card design is **professional and print-ready**. The CR80 format and print CSS are well-implemented. However, the **missing authentication is a critical security issue**.

---

## 10. Database Administration (Backup/Restore)

### ✅ What's Implemented
- **Backup via pg_dump**: Generates `.sql` file streamed to browser download
- **Restore via psql**: Uploads `.sql` file, writes to temp, restores
- **Admin-only access**: `@user_passes_test(is_admin)` decorator
- **Confirmation dialog**: Restore requires typing "RESTORE" to confirm
- **File extension validation**: Only `.sql` files accepted
- **Temp file cleanup**: Uses `tempfile.NamedTemporaryFile` with cleanup in `finally`
- **Audit logging on restore**: Creates AuditLog entry after successful restore
- **Cross-platform pg_bin detection**: `get_pg_bin()` searches for PostgreSQL binaries across versions

### ⚠️ Issues Found

| # | Severity | Issue | Details |
|---|----------|-------|---------|
| 1 | **CRITICAL** | SQL injection via file upload | The restore function writes an uploaded `.sql` file directly to `psql` stdin. A malicious `.sql` file could contain `DROP DATABASE`, `CREATE ROLE`, or even `COPY ... TO '/etc/passwd'` commands. Only checking file extension (`.sql`) is insufficient. |
| 2 | **HIGH** | No file size limit on upload | An attacker (or careless admin) could upload a multi-GB file, exhausting server disk/memory. |
| 3 | **HIGH** | Database password in environment variable | `PGPASSWORD` is passed via environment to subprocess. While necessary, this is visible in `/proc/pid/environ` on Linux. Consider using `.pgpass` file instead. |
| 4 | **MEDIUM** | No backup encryption | Backups are downloaded as plain-text SQL. Per `security_protocol.md`, backups should be encrypted. |
| 5 | **MEDIUM** | No automated backup schedule | `security_protocol.md` requires daily automated encrypted backups. Current implementation is manual-only. |
| 6 | **MEDIUM** | Missing `AuditLog` import in views.py | `restore_database` references `AuditLog` but the import `from administration.models import AuditLog` is missing at the top of the file. This will cause a `NameError` at runtime. |
| 7 | **LOW** | Backup doesn't log to AuditLog | Only restore is audit-logged, not backup downloads. |

### Recommendations
- Add file size limit (e.g., 500MB max)
- Add AuditLog import to `administration/views.py`
- Implement backup encryption (GPG or AES)
- Add automated backup via management command + cron/celery
- Consider restricting restore to superusers only (not just Admin group)
- Log backup downloads in AuditLog

---

## 11. Additional Security Findings

| # | Severity | Issue | Location | Details |
|---|----------|-------|----------|---------|
| 1 | **CRITICAL** | `.env` contains secrets in repo | `backend/.env` | `DB_PASSWORD=lanud2026`, `SECRET_KEY=rX0X...`, `ENCRYPTION_KEY=CBZCl...` are all in the `.env` file. If this file is committed to version control, ALL secrets are compromised. |
| 2 | **CRITICAL** | `DEBUG=True` in .env | `backend/.env` | Debug mode exposes stack traces, SQL queries, and internal paths to any user who triggers an error. Must be `False` in production. |
| 3 | **HIGH** | `ALLOWED_HOSTS = '*'` default | `settings.py` | If `ALLOWED_HOSTS` env var is not set, it defaults to `'*'`, accepting requests from any hostname. Enables HTTP Host header attacks. |
| 4 | **HIGH** | `SECRET_KEY` has insecure fallback | `settings.py` | `SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-fallback-do-not-use-in-production')` – If env var is missing, the fallback key is used. This is a known weak key. |
| 5 | **HIGH** | API endpoints lack authentication | `urls.py` | `load_postos`, `load_sucos`, `load_aldeias` are outside any auth requirement (placed before `accounts/` in urlpatterns). These expose geographic data without authentication. |
| 6 | **MEDIUM** | `db.sqlite3` exists alongside PostgreSQL config | `backend/` | An SQLite database file exists, suggesting it may have been used during development. May contain stale data or credentials. Should be removed. |
| 7 | **MEDIUM** | No rate limiting | Global | No rate limiting on login, API, or any views. Vulnerable to brute force attacks. |
| 8 | **MEDIUM** | No MFA implemented | Global | `security_protocol.md` requires "Mandatory MFA for Admin and Doctor roles" but no MFA is implemented anywhere. |
| 9 | **MEDIUM** | Media files served without auth | `settings.py` | `if settings.DEBUG: urlpatterns += static(settings.MEDIA_URL, ...)` serves patient photos and QR codes without authentication. In production, media should be served through Django with auth checks or via signed URLs. |
| 10 | **LOW** | No `.gitignore` visible | Root | Cannot confirm if `.env`, `db.sqlite3`, `__pycache__`, `media/` are excluded from version control. |

---

## 12. Compliance vs. Security Protocol

| Requirement (from `security_protocol.md`) | Status | Notes |
|---|---|---|
| RBAC with 5 roles | ✅ Partially | Roles exist but need fine-tuning |
| MFA for Admin/Doctor | ❌ **Not Implemented** | No MFA anywhere |
| Session timeout 15 min inactivity | ❌ **Not Implemented** | Set to 8 hours, no idle detection |
| Database encryption for PHI | ✅ Partially | `EncryptedTextField` exists but unclear which fields use it |
| Mandatory HTTPS (TLS 1.3) | ❌ **Not Enforced** | `SECURE_SSL_REDIRECT=False` |
| PII masking in reports | ❌ **Not Implemented** | No evidence of PII masking |
| Audit log for every action | ❌ **Partially** | Only LOGIN/LOGOUT logged, no CRUD |
| Daily encrypted backups | ❌ **Not Implemented** | Manual only, unencrypted |
| Point-in-time recovery (WAL) | ❓ **Unknown** | PostgreSQL config not audited |
| Failover hot-standby | ❌ **Not Implemented** | Single database instance |
| GDPR/HIPAA audit | ❌ **Not Done** | Multiple violations identified |
| No plain text patient names in logs | ⚠️ **Violated** | `AuditLog.object_repr` stores "User X logged in" – acceptable, but CRUD logs may store patient names |
| Secure media storage (S3) | ❌ **Not Implemented** | Local filesystem storage |

---

## 13. Priority Fix List (Ordered by Severity)

### 🔴 CRITICAL (Fix Immediately)
1. **Remove `.env` from version control** and add to `.gitignore`
2. **Set `DEBUG=False`** in production
3. **Fix encryption key fallback** – raise error instead of generating random key
4. **Add authentication to printing views** (`preview_card`, `print_card_trigger`)
5. **Validate/sanitize SQL restore uploads** or restrict to superuser only with additional safeguards

### 🟠 HIGH (Fix Before Production)
6. Add `PermissionRequiredMixin` to `RolePermissionMatrixView`
7. Implement comprehensive audit logging for all CRUD operations
8. Enforce session idle timeout (15 minutes per protocol)
9. Set `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, `SECURE_SSL_REDIRECT=True`
10. Add authentication to API endpoints (`load_postos`, `load_sucos`, `load_aldeias`)
11. Fix `custom_logout` to require POST only
12. Fix missing `AuditLog` import in `administration/views.py`
13. Set proper `ALLOWED_HOSTS` (remove `*` default)
14. Add password validation in staff registration form
15. Register models in Django admin

### 🟡 MEDIUM (Fix Soon)
16. Add Content Security Policy headers
17. Implement rate limiting (django-ratelimit or django-axes)
18. Implement MFA for Admin/Doctor roles (django-otp or django-allauth)
19. Fix permission codename collision in permission matrix
20. Add audit log viewer UI
21. Add dashboard input validation (year parameter)
22. Add backup encryption
23. Implement automated daily backups
24. Serve static assets locally (not CDN) for offline reliability
25. Add file size limits on restore upload

### 🟢 LOW (Nice to Have)
26. Add breadcrumb standardization in base template
27. Remove `db.sqlite3` from project
28. Add footer to base template
29. Customize Django admin branding
30. Remove dead `DefaultTetumMiddleware` code

---

## Files Audited

| File | Purpose |
|------|---------|
| `clinic_core/settings.py` | Django settings |
| `clinic_core/middleware.py` | Audit + language middleware |
| `clinic_core/views.py` | Dashboard + CSRF error views |
| `clinic_core/urls.py` | Root URL configuration |
| `clinic_core/fields.py` | Encryption field |
| `staff/models.py` | Staff, Department, Category, Position models |
| `staff/views.py` | Staff CRUD + Role CRUD views |
| `staff/rbac_views.py` | Permission matrix + User-role mapper |
| `staff/forms.py` | Staff creation/update forms |
| `staff/signals.py` | Auto-group assignment signal |
| `staff/urls.py` | Staff URL routes |
| `staff/admin.py` | Admin registration (empty) |
| `staff/apps.py` | App config with signal loading |
| `administration/models.py` | AuditLog model |
| `administration/views.py` | Backup/Restore views |
| `administration/urls.py` | Admin URL routes |
| `administration/admin.py` | Admin registration (empty) |
| `printing/views.py` | Card preview/print views |
| `printing/utils.py` | QR/Barcode generation |
| `printing/urls.py` | Printing URL routes |
| `templates/base.html` | Base layout with sidebar |
| `templates/dashboard.html` | Main dashboard |
| `templates/403_csrf.html` | CSRF error page |
| `templates/staff/*.html` | All 10 staff templates |
| `templates/administration/backup_restore.html` | Backup/Restore UI |
| `templates/printing/card_preview.html` | Patient card template |
| `backend/.env` | Environment variables |
| `security_protocol.md` | Security requirements document |

---

*End of Audit Report*
