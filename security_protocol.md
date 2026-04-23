# Security & Compliance Protocol
Professional Medical Standard

## 1. Authentication & Authorization
- **RBAC (Role-Based Access Control)**:
    - `Administrator`: Full system access, audit log management.
    - `Doctor`: View/Edit Medical Records, Prescriptions, Lab Results.
    - `Reception`: Register Patients, Billing, Card Printing.
    - `Nurse`: Vital signs entry, view patient list.
    - `Staff`: Viewing only (No edit).
- **MFA**: Mandatory Multi-Factor Authentication for Admin and Doctor roles.
- **Session Timeout**: Maximum 15 minutes of inactivity.

## 2. Data Protection (Medical Privacy)
- **Data at Rest**: PostgreSQL database encryption for sensitive fields (PHI - Protected Health Information).
- **Data in Transit**: Mandatory HTTPS (TLS 1.3) for all communications.
- **PII Masking**: Partial masking of patient identifiers in generic reports.

## 3. Audit Logging (Immutable)
Every request to the system must be logged in an `AuditLog` table:
- `timestamp`: DateTime
- `user`: ForeignKey(User)
- `action`: CharField (VIEW, EDIT, DELETE, LOGIN)
- `module`: CharField (PATIENT, BILLING, MEDICAL)
- `object_id`: UUID of the record
- `ip_address`: CharField
- `changes`: JSONField (Diff of old vs new values)

## 4. Disaster Recovery
- **Daily Backups**: Automated encrypted backups to offsite S3/Private Cloud.
- **Point-in-Time Recovery**: Database configured for WAL (Write-Ahead Logging).
- **Failover**: Secondary database node in hot-standby mode.

## 5. Compliance Checklist
- [ ] GDPR/HIPAA-ready architectural audit.
- [ ] No plain text storage of patient names in logs.
- [ ] Secure media storage (AWS S3 with private access policies).
