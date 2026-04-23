# Database Models Representation
Clinic Professional Management System

## Overview
This document defines the Django models and their relationships to ensure a hospital-grade data structure.

---

## 1. Patient App
Models for core identity and registration.

### `Patient`
- `uuid`: UUIDField (Primary Key)
- `patient_id`: CharField (Unique, Auto-generated)
- `full_name`: CharField
- `date_of_birth`: DateField
- `gender`: CharField (Choices: Male, Female, Other)
- `address`: TextField
- `phone_number`: CharField
- `emergency_contact_name`: CharField
- `emergency_contact_phone`: CharField
- `qr_code_image`: ImageField
- `barcode_image`: ImageField
- `created_at`: DateTimeField
- `updated_at`: DateTimeField

---

## 2. Medical Record App
Models for clinical data.

### `Visit`
- `uuid`: UUIDField
- `patient`: ForeignKey(Patient)
- `doctor`: ForeignKey(User)
- `visit_date`: DateTimeField
- `queue_number`: IntegerField (Daily Reset)
- `complaint`: TextField (Keluhan Utama)
... (rest of fields)

### `DailyQueue`
- `date`: DateField (Unique)
- `current_number`: IntegerField (To track the last issued number for the day)
- `department`: CharField (Optional, e.g., General, Dental)

### `Prescription`
- `visit`: OneToOneField(Visit)
- `notes`: TextField
- `created_at`: DateTimeField

### `PrescriptionItem`
- `prescription`: ForeignKey(Prescription)
- `medicine_name`: CharField
- `dosage`: CharField
- `instructions`: CharField

---

## 3. Billing App
Models for financial transactions.

### `Invoice`
- `invoice_number`: CharField (Unique)
- `visit`: OneToOneField(Visit)
- `total_amount`: DecimalField
- `tax_amount`: DecimalField
- `discount`: DecimalField
- `status`: CharField (Unpaid, Paid, Partially Paid)
- `payment_method`: CharField
- `created_at`: DateTimeField

---

## 4. Laboratory App
Models for diagnostic tests.

### `LabRequest`
- `visit`: ForeignKey(Visit)
- `test_type`: CharField
- `request_date`: DateTimeField
- `status`: CharField (Pending, Sample Collected, Completed)

### `LabResult`
- `lab_request`: OneToOneField(LabRequest)
- `result_details`: JSONField
- `attachment`: FileField (PDF Results)
- `verified_by`: ForeignKey(User)

---

## Entity Relationship Summary
- **One-to-Many**: Patient → Visits, Visit → LabRequests, Prescription → Items.
- **One-to-One**: Visit ↔ Prescription, Visit ↔ Invoice.
- **UUIDs**: All tables use UUIDs for primary keys to ensure data security and ease of synchronization.
