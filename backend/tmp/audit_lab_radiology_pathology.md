# Audit Report: Laboratory, Radiology & Pathology Apps
**Date:** 2026-04-12  
**Scope:** D:\pasient_system\backend — laboratory, radiology, pathology Django apps  

---

## 1. LABORATORY APP

### 1.1 What's Implemented ✅
| Component | Status | Notes |
|-----------|--------|-------|
| **Models** (4 models) | ✅ Good | `LabTest`, `LabRequest`, `LabResult`, `LabResultAttachment` |
| **Views** (3 views) | ✅ Functional | `lab_request_create`, `lab_result_input`, `lab_dashboard` |
| **URLs** (3 routes) | ✅ Complete | Dashboard, request create, result input |
| **Admin** (3 registered) | ✅ Good | All models registered with proper list_display/filters |
| **Templates** (5 templates) | ✅ Comprehensive | Dashboard, request form, result form, CBC form, comprehensive form |
| **Template tags** | ✅ Present | `get_item`, `replace`, `get_cbc_range` custom filters |
| **Seed script** | ✅ Present | `seed_lab_tests.py` with 3-column test layout |
| **i18n** | ✅ Good | All user-facing strings use `gettext_lazy` / `gettext` |
| **UUID primary keys** | ✅ Correct | `LabRequest` and `LabResult` use UUID PKs |
| **Workflow states** | ✅ 4 states | PENDING → SAMPLE_COLLECTED → IN_PROGRESS → COMPLETED |
| **CBC reference ranges** | ✅ Excellent | Age/gender-specific: adult_m, adult_f, child, neonate |
| **Comprehensive result form** | ✅ Excellent | Serology, Biochemistry, Urinalysis, Microscopy, Microbiology sections |
| **Audit logging** | ✅ Present | `log_visit_action()` called on request create and result input |
| **Print support** | ✅ Good | CSS `@media print` styles on all forms |
| **File attachments** | ✅ Multi-file | Both legacy single attachment and new multi-attachment model |
| **Date filtering** | ✅ Present | Dashboard filters by date |

### 1.2 Issues Found 🔴

**CRITICAL:**

1. **No forms.py — No server-side validation**  
   - All views use raw `request.POST.get()` without Django Forms or validation.
   - No input sanitization on result values (CBC values, biochemistry values, etc.).
   - A malicious or accidental POST could inject invalid data into `result_data` JSONField.
   - **Risk:** Data integrity issues, potential XSS if result_data is rendered unsanitized.

2. **No permission/role checks beyond `@login_required`**  
   - Any logged-in user (receptionist, billing clerk) can create lab requests, input results, and mark them as completed.
   - A professional clinic needs role-based access: only doctors create requests, only lab techs input results, only senior lab techs verify.

3. **LabRequest uses `OneToOneField` to Visit**  
   - `visit = models.OneToOneField(Visit, ...)` means only ONE lab request per visit.
   - Real clinics often need multiple lab requests per visit (e.g., initial CBC, then follow-up biochemistry 2 hours later).
   - Should be `ForeignKey` with a unique constraint only if intentional.

4. **No `forms.py` file exists at all** — the app has no Django Form classes.

**HIGH:**

5. **`verified_by` is set to `request.user` automatically on save** — not a separate verification step.
   - The same person who inputs results also becomes the verifier. A real lab requires a separate verification/approval step by a senior technician or pathologist.

6. **Two `<select name="status">` elements in `cbc_result_form.html`**  
   - Line 1: `<input type="hidden" name="status" value="COMPLETED">` 
   - Line 2: A visible `<select name="status">` lower in the form.
   - The hidden input will conflict with the select. Browser behavior is unpredictable — whichever appears last in POST data wins.

7. **No search functionality on dashboard**  
   - Dashboard only filters by date. No patient name search, no status filter, no urgency filter.

8. **No pagination on dashboard**  
   - If a busy lab has 200+ requests per day, the entire list renders in one page.

**MEDIUM:**

9. **`GinIndex` with `gin_trgm_ops` requires PostgreSQL `pg_trgm` extension**  
   - But the project uses `db.sqlite3` (seen in backend directory). These indexes will fail on SQLite.
   - Either the project must enforce PostgreSQL, or these indexes should be conditional.

10. **No test for result data structure validation**  
    - `result_data = models.JSONField(...)` accepts any JSON. No schema validation ensures CBC data has all required keys.

11. **Lab number (`lab_no`) is not auto-generated**  
    - It's a manually typed field. Professional labs need sequential, auto-incrementing lab numbers per day.

12. **No sample collection tracking**  
    - Status `SAMPLE_COLLECTED` exists but there's no dedicated sample collection view, timestamp, or collector field. It's just a status dropdown.

13. **Bare `except:` not used, but `ObjectDoesNotExist` import is done inside the function** — minor code smell.

14. **Seed script (`seed_lab_tests.py`) is a standalone script, not a management command** — inconsistent with radiology/pathology which use management commands.

### 1.3 Missing Features for Professional Clinic 🟡

- **Quality Control (QC) tracking** — No internal QC result logging.
- **Reference range management** — Ranges are hardcoded in views.py, not database-configurable.
- **Critical value alerts** — No mechanism to flag dangerously abnormal results.
- **Turnaround time (TAT) tracking** — No metric for request-to-completion time.
- **Result history/versioning** — OneToOne means only one result per request; no amendment tracking.
- **Barcode/label printing for samples** — No sample label generation.
- **Integration with billing** — Lab tests aren't linked to invoice line items.
- **Rejection workflow** — No way to reject a sample (hemolyzed, insufficient quantity, etc.).
- **External lab referral** — No mechanism to send tests to external labs.

---

## 2. RADIOLOGY APP

### 2.1 What's Implemented ✅
| Component | Status | Notes |
|-----------|--------|-------|
| **Models** (4 models) | ✅ Good | `RadiologyTest`, `RadiologyRequest`, `RadiologyResult`, `RadiologyResultAttachment` |
| **Views** (3 views) | ✅ Functional | Request create, result input, dashboard |
| **URLs** (3 routes) | ✅ Complete | Dashboard, request, result |
| **Admin** (3 registered) | ✅ Good | All models registered |
| **Templates** (3 templates) | ✅ Good | Dashboard, request form, result form |
| **Seed command** | ✅ Management command | 30 radiology test types (X-ray focused) |
| **i18n** | ✅ Partial | Mixed — some labels in Portuguese/Tetum ("Data Riquest", "Medico") |
| **UUID PKs** | ✅ Correct | Request and Result use UUIDs |
| **Workflow states** | ✅ 3 states | PENDING → IN_PROGRESS → COMPLETED |
| **Findings + Impression** | ✅ Good | Separate fields for findings and impression (standard radiology report) |
| **Print support** | ✅ Good | Print-optimized CSS |
| **Audit logging** | ✅ Present | `log_visit_action()` on both request and result |

### 2.2 Issues Found 🔴

**CRITICAL:**

1. **No forms.py — No server-side validation** (same as lab).

2. **No permission checks beyond `@login_required`** (same as lab).

3. **`OneToOneField` to Visit** — Only one radiology request per visit. A patient might need multiple imaging studies in the same visit.

4. **Bare `except:` clause in `radiology_result_input`**  
   ```python
   try:
       existing_result = rad_req.result
   except:
       existing_result = None
   ```
   This catches ALL exceptions including `SystemExit`, `KeyboardInterrupt`, etc. Should be `except RadiologyResult.DoesNotExist:` or `except ObjectDoesNotExist:`.

**HIGH:**

5. **No `SAMPLE_COLLECTED` status** — Radiology has only 3 states (PENDING, IN_PROGRESS, COMPLETED). Missing "SCHEDULED" or "PATIENT_ARRIVED" intermediate state.

6. **No search or pagination on dashboard** (same as lab).

7. **`RadiologyTest` model has no `code` field** — Unlike `LabTest` which has a `code`. Radiology tests should have standard codes (CPT, LOINC, or local codes).

8. **No urgency field on `RadiologyRequest`** — Unlike lab which has NORMAL/URGENT. Urgent X-rays (trauma) need prioritization.

**MEDIUM:**

9. **`verified_by` auto-set** — Same issue as lab; no separate verification step.

10. **No radiation dose tracking** — Professional radiology departments track patient radiation exposure (especially for CT, if added later).

11. **No contrast media tracking** — No field to record if contrast was used (important for patient safety / allergies).

12. **Template labels mix languages** — "Data Riquest", "Medico" (Portuguese) mixed with English. Should be consistent via i18n.

13. **No DICOM support** — File upload accepts `.dcm` in the template's `accept` attribute, but there's no DICOM viewer or PACS integration. Files are just stored as generic uploads.

### 2.3 Missing Features for Professional Clinic 🟡

- **Scheduling/appointment for imaging** — No time slot management.
- **Patient preparation instructions** — No field for prep notes (fasting, contrast allergy check, etc.).
- **Modality tracking** — No field to record imaging modality (X-ray, Ultrasound, CT, MRI).
- **Technologist notes** — No separate field for tech comments during imaging.
- **Comparison with prior studies** — No link to previous radiology results for the same patient.
- **Billing integration** — Not linked to invoice items.
- **Report templates** — No predefined templates for common findings.
- **Body part/laterality** — No structured field for body part and left/right.

---

## 3. PATHOLOGY APP

### 3.1 What's Implemented ✅
| Component | Status | Notes |
|-----------|--------|-------|
| **Models** (4 models) | ✅ Good | `PathologyTest`, `PathologyRequest`, `PathologyResult`, `PathologyResultAttachment` |
| **Views** (3 views) | ✅ Functional | Request create, result input, dashboard |
| **URLs** (3 routes) | ✅ Complete | Dashboard, request, result |
| **Admin** (3 registered) | ✅ Good | All models registered |
| **Templates** (3 templates) | ✅ Good | Dashboard, request form (very detailed paper-form replica), result form |
| **Seed command** | ✅ Management command | 22 chemistry test types |
| **Specimen/tube tracking** | ✅ Present | 10 tube type fields (SST, EDTA, ESR, etc.) |
| **Clinical history** | ✅ Present | Free-text field for clinical context |
| **Billing type** | ✅ Present | Outpatient/Inpatient/Private/Government |
| **Fasting flag** | ✅ Present | Boolean field |
| **Workflow states** | ✅ 4 states | PENDING → SAMPLE_COLLECTED → IN_PROGRESS → COMPLETED |
| **i18n** | ✅ Bilingual | Form labels in English + Portuguese/Tetum |
| **UUID PKs** | ✅ Correct | Request and Result use UUIDs |
| **Print support** | ✅ Excellent | Paper-form replica with proper print CSS |
| **Audit logging** | ✅ Present | `log_visit_action()` on both request and result |

### 3.2 Issues Found 🔴

**CRITICAL:**

1. **No forms.py — No server-side validation** (same pattern as lab/radiology).

2. **No permission checks beyond `@login_required`** (same).

3. **`OneToOneField` to Visit** — Same limitation; only one pathology request per visit.

4. **Bare `except:` in `pathology_result_input`** — Same issue as radiology.
   ```python
   try:
       existing_result = patho_req.result
   except:
       existing_result = None
   ```

5. **Result is free-text only (`result_text`)** — Unlike the lab app which has structured `result_data` JSONField, pathology results are just a textarea. For a pathology/chemistry department, results should be structured (test name → value → unit → reference range → flag).

**HIGH:**

6. **No structured result data** — `PathologyResult` has no `result_data` JSONField. The 22 chemistry tests (CBC, Glucose, Uric Acid, etc.) have no structured storage. This is a significant gap compared to the laboratory app.

7. **Tube fields are individual CharField columns** — 10 separate `tube_*` fields is poor database design. Should be a related model or JSONField for extensibility.

8. **No search or pagination on dashboard** (same as others).

9. **`PathologyTest` has no `code` field** — No test codes for standardization.

10. **No urgency field** — Unlike lab which has NORMAL/URGENT.

**MEDIUM:**

11. **`verified_by` auto-set** — Same as lab/radiology.

12. **Typo: `clinica_history`** — Should be `clinical_history` (English) or consistently use Portuguese.

13. **`pregnant` and `week` fields in template are not saved** — The request form has pregnancy/week inputs, but these fields don't exist on the `PathologyRequest` model. Data is lost on form submission.

14. **Collection Date/Time fields in template are not saved** — Same issue — the form shows collection date/time inputs but they're not model fields and not in the POST handler.

### 3.3 Missing Features for Professional Clinic 🟡

- **Structured result entry** — Needs a structured form like lab's comprehensive form, not just free text.
- **Reference ranges per test** — No reference range data for pathology tests.
- **Histopathology workflow** — No specimen description, gross examination, microscopic examination, or diagnosis fields typical of tissue pathology.
- **Cytology support** — No Pap smear result structure despite `tube_pap` field existing.
- **Specimen tracking with barcodes** — No barcode generation for specimens.
- **Turn-around time tracking** — No TAT metrics.
- **Result amendment/correction workflow** — No versioning.
- **Billing integration** — Not connected to invoicing.

---

## 4. CROSS-CUTTING ISSUES (ALL THREE APPS)

### 4.1 Security & Permissions 🔴
| Issue | Severity | Detail |
|-------|----------|--------|
| No role-based access | CRITICAL | Any logged-in user can access any endpoint. Need `@permission_required` or group checks. |
| No CSRF exemption issues | ✅ OK | All forms properly use `{% csrf_token %}`. |
| No file type validation on upload | HIGH | Server accepts any file despite template `accept` attribute (client-side only). |
| No file size limits | HIGH | No `MAX_UPLOAD_SIZE` validation. Users could upload very large files. |

### 4.2 Code Quality
| Issue | Severity | Detail |
|-------|----------|--------|
| Zero unit tests | HIGH | All three `tests.py` files are empty stubs. |
| No forms.py in any app | HIGH | All input handling is raw POST data. |
| Bare except clauses | MEDIUM | Radiology and pathology views use bare `except:`. |
| Imports inside functions | LOW | Several views import models/utils inside POST handlers instead of at top of file. |
| No type hints | LOW | No function signatures use type hints. |
| No docstrings | LOW | No view functions have docstrings. |

### 4.3 Database Design
| Issue | Severity | Detail |
|-------|----------|--------|
| OneToOne Visit constraint | HIGH | All three apps limit to one request per visit. Should likely be ForeignKey. |
| GinIndex on SQLite | MEDIUM | PostgreSQL-specific indexes on a project using SQLite will cause migration errors. |
| No database constraints | MEDIUM | No `CheckConstraint`, `UniqueConstraint`, or custom validators on models. |
| No `updated_at` on Request models | LOW | Requests don't track when they were last modified. |

### 4.4 UX / Templates
| Issue | Severity | Detail |
|-------|----------|--------|
| No pagination | HIGH | All dashboards render all results for a date without pagination. |
| No search | HIGH | No patient name/ID search on dashboards. |
| No confirmation dialogs | MEDIUM | Status changes (especially to COMPLETED) have no "Are you sure?" confirmation. |
| No loading indicators | LOW | Form submissions have no loading state. |
| Mixed language labels | LOW | English/Portuguese/Tetum mixed inconsistently. |

---

## 5. WORKFLOW ANALYSIS

### 5.1 Laboratory Workflow
```
Doctor creates request → [PENDING]
  → Lab collects sample → [SAMPLE_COLLECTED]  ← No dedicated view for this step
    → Lab tech enters results → [IN_PROGRESS]
      → Lab tech completes → [COMPLETED]  ← No separate verification step
```
**Assessment:** Mostly correct but missing sample collection and verification steps as distinct operations.

### 5.2 Radiology Workflow
```
Doctor creates referral → [PENDING]
  → Technologist begins imaging → [IN_PROGRESS]
    → Radiologist reports → [COMPLETED]  ← No separate reporting vs verification
```
**Assessment:** Simplified but functional. Missing patient scheduling and separate technologist vs radiologist roles.

### 5.3 Pathology Workflow
```
Doctor creates request → [PENDING]
  → Lab collects sample → [SAMPLE_COLLECTED]  ← No dedicated view
    → Lab processes → [IN_PROGRESS]
      → Results entered → [COMPLETED]  ← Free text only, no structured data
```
**Assessment:** Has the right states but the result entry is unstructured (free text) which defeats the purpose of having specific chemistry tests defined.

---

## 6. SUMMARY SCORECARD

| Category | Laboratory | Radiology | Pathology |
|----------|-----------|-----------|-----------|
| Models completeness | 8/10 | 7/10 | 6/10 |
| Views completeness | 7/10 | 6/10 | 5/10 |
| Template quality | 9/10 | 7/10 | 8/10 |
| Workflow correctness | 6/10 | 5/10 | 4/10 |
| Security/permissions | 2/10 | 2/10 | 2/10 |
| Code quality | 4/10 | 3/10 | 3/10 |
| Test coverage | 0/10 | 0/10 | 0/10 |
| **Overall** | **5.1/10** | **4.3/10** | **4.0/10** |

---

## 7. TOP PRIORITY RECOMMENDATIONS

1. **Add Django Forms with validation** — Create `forms.py` for each app with proper field validation, cleaning, and error handling.
2. **Add role-based permissions** — Use Django's permission framework: `lab_technician`, `radiologist`, `pathologist`, `doctor` groups with appropriate permissions.
3. **Change OneToOneField to ForeignKey** — Allow multiple requests per visit for all three apps.
4. **Add structured result data to Pathology** — Add `result_data = JSONField()` to `PathologyResult` and create a structured result entry form (like lab's comprehensive form).
5. **Fix bare except clauses** — Replace with specific `ObjectDoesNotExist` exceptions.
6. **Add pagination and search** — All three dashboards need paginated results and patient search.
7. **Add unit tests** — Write tests for model creation, view access, workflow state transitions, and permission checks.
8. **Fix pathology template data loss** — Add `pregnant`, `pregnancy_week`, `collection_date`, `collection_time` fields to the model, or remove them from the template.
9. **Fix duplicate status field in CBC form** — Remove the hidden input that conflicts with the select dropdown.
10. **Add separate verification step** — Implement a distinct "verify result" action with a different user than the one who entered the result.
