# Audit Report: Billing, Pharmacy & Appointments Apps
**Clinic Management System — D:\pasient_system\backend**
**Audit Date: 2026-04-12**

---

## Executive Summary

| App | Status | Completeness |
|---|---|---|
| **Billing** | ✅ Substantially complete | ~85% |
| **Pharmacy** | ✅ Substantially complete | ~80% |
| **Appointments** | ❌ Empty / Not implemented | ~0% |

The **billing** and **pharmacy** apps are well-built with proper models, views, templates, admin integration, and i18n support. The **appointments** app is a skeleton with no models, views, or templates — it is only registered in `INSTALLED_APPS` and has no `urls.py`.

---

## 1. BILLING APP — Detailed Analysis

### 1.1 Models (`billing/models.py`) — ✅ Good

**Implemented models:**
| Model | Fields | Notes |
|---|---|---|
| `ServiceCategory` | name, code, icon, order, is_active | Proper ordering, active flag |
| `ServicePrice` | category (FK), name, code, price, description, is_active, timestamps | Good relationship with category |
| `Invoice` | uuid (PK), invoice_number, visit (O2O), patient (FK), subtotal, discount, total_amount, amount_paid, status, payment_method, notes, created_by, timestamps, paid_at | Comprehensive |
| `InvoiceItem` | invoice (FK), service (FK), category (FK), description, quantity, unit_price | Line-item support |
| `Payment` | uuid (PK), invoice (FK), amount, payment_method, reference, notes, received_by, created_at | Multi-payment tracking |

**Strengths:**
- UUID primary keys on Invoice and Payment (security-friendly)
- `recalculate()` method properly aggregates line items and updates status
- `generate_invoice_number()` auto-generates sequential daily numbers (INV-YYYYMMDD-NNNN)
- `balance_due` computed property
- GinIndex with trigram for invoice number search (PostgreSQL-optimized)
- Composite indexes on patient+created_at, status, created_at
- Custom permissions: `view_menu_billing`, `can_export_invoices`
- Proper `on_delete` behavior (CASCADE, PROTECT, SET_NULL as appropriate)
- Full i18n with `gettext_lazy`

**Issues Found:**
1. **🔴 No tax_amount field** — The `models.md` spec calls for `tax_amount: DecimalField` but the implementation has no tax handling. For a professional clinic, tax/VAT support may be needed.
2. **🟡 No refund model** — There is no `Refund` or `CreditNote` model. Overpayments or cancellations have no refund tracking.
3. **🟡 No invoice edit/update view** — Invoices can be created but not edited after creation. No way to add items to an existing invoice.
4. **🟡 No invoice cancellation view** — Status 'CANCELLED' exists but there is no view/URL to cancel an invoice.
5. **🟡 `recalculate()` double-save issue** — `payment_create` sets `amount_paid` then calls `recalculate()` which calls `self.save()`, but `amount_paid` was set on the in-memory object before calling recalculate. This works but is fragile — if `recalculate()` re-fetched from DB, payments could be lost.
6. **🟡 No forms.py** — All validation is done in views with raw `request.POST`. No Django Forms or ModelForms for server-side validation. This means:
   - No CSRF-protected field-level validation
   - No cleaning/sanitization of text fields
   - Decimal parsing uses bare `Decimal()` which can raise exceptions on malformed input (partially caught with try/except)
7. **🟡 Payment overpayment not prevented** — `payment_create` doesn't check if `amount > balance_due`, allowing overpayment.
8. **🟢 Minor: `service_price_delete` does hard delete** — Should consider soft-delete since InvoiceItems reference ServicePrice with `SET_NULL`.

### 1.2 Views (`billing/views.py`) — ✅ Good

**Implemented views (17 total):**
| View | Method | Auth | Notes |
|---|---|---|---|
| `billing_dashboard` | GET | `@login_required` | Date filtering, daily stats |
| `invoice_create` | GET/POST | `@login_required` | AJAX patient search, service catalog |
| `invoice_create_for_visit` | GET/POST | `@login_required` | Pre-linked to visit |
| `invoice_detail` | GET | `@login_required` | Full detail with payments |
| `invoice_print` | GET | `@login_required` | Print-friendly layout |
| `payment_create` | GET/POST | `@login_required` | Records payment |
| `service_category_list` | GET | `@login_required` | Lists all categories |
| `service_category_add` | GET/POST | `@login_required` | Add category |
| `service_category_edit` | GET/POST | `@login_required` | Edit category |
| `service_price_add` | GET/POST | `@login_required` | Add service price |
| `service_price_edit` | GET/POST | `@login_required` | Edit service price |
| `service_price_delete` | GET/POST | `@login_required` | Delete service price |
| `api_search_patients` | GET (JSON) | `@login_required` | AJAX patient search |
| `api_services_by_category` | GET (JSON) | `@login_required` | AJAX service loading |
| `api_patient_visits` | GET (JSON) | `@login_required` + `@permission_required` | Patient visit list |
| `billing_report` | GET | `@login_required` | Date range reporting with category breakdown |
| `patient_billing_history` | GET | `@login_required` | Per-patient billing history |

**Strengths:**
- Good use of `select_related` and `prefetch_related` for query optimization
- Proper AJAX APIs for dynamic UI
- Reports with category breakdown and date range filters
- Prevention of duplicate invoices per visit

**Issues Found:**
1. **🔴 Inconsistent permission checks** — Only `api_patient_visits` uses `@permission_required`. All other views only check `@login_required`. A nurse or receptionist could create/modify service prices or view all invoices. Missing role-based access control.
2. **🔴 Duplicate code** — `invoice_create` and `invoice_create_for_visit` share ~80% identical POST-handling code. Should be refactored into a shared helper.
3. **🟡 No pagination on dashboard** — Dashboard uses `[:200]` hard limit. For busy clinics this could miss invoices.
4. **🟡 No pagination on billing_report** — Report uses `[:100]` hard limit.
5. **🟡 No search on dashboard** — Cannot search by patient name or invoice number on the main billing dashboard.
6. **🟡 `api_search_patients` imports Q redundantly** — `Q` is imported at top of file AND again inside the function.

### 1.3 URLs (`billing/urls.py`) — ✅ Good
- 17 URL patterns, well-organized with comments
- Clean UUID-based URLs for invoices
- REST-like API endpoints

### 1.4 Admin (`billing/admin.py`) — ✅ Good
- All 4 models registered with proper admin configuration
- Inline support for InvoiceItems and Payments
- List filters and search fields configured

### 1.5 Templates (11 files) — ✅ Good
- Full i18n with `{% trans %}` tags throughout
- Bootstrap 5 with Bootstrap Icons
- Responsive tables and cards
- Print-friendly invoice template with proper `@media print` CSS
- AJAX-powered patient search and service catalog on invoice form
- Dynamic row add/remove with JS for line items
- Real-time subtotal/total calculation in JavaScript
- Patient visit loading via AJAX
- Proper `{% csrf_token %}` on all forms

**Issues Found:**
1. **🟡 No CSRF error handling in AJAX** — fetch() calls don't include CSRF token for any future POST APIs
2. **🟡 Invoice form submit button** — Button says "Create Invoice" even when editing (though edit isn't implemented, `editing` variable is passed)

### 1.6 Tests (`billing/tests.py`) — ❌ Empty
- No unit tests whatsoever

---

## 2. PHARMACY APP — Detailed Analysis

### 2.1 Models (`pharmacy/models.py`) — ✅ Good

**Implemented models:**
| Model | Fields | Notes |
|---|---|---|
| `Medicine` | name, strength, form, code, unit, stock, min_stock, description, is_active, timestamps | Comprehensive with 8 unit types, 11 form types |
| `StockEntry` | medicine (FK), source_type, donor_name, quantity, remaining_qty, expiry_date, batch_number, supplier, purchase_date, unit_price, notes, created_by, created_at | FIFO-ready with remaining_qty |
| `Prescription` | uuid (PK), visit (O2O), has_allergy, allergy_medicine, prescription_text, doctor, dispensing_status, dispensed_by, dispensed_at, dispensing_notes | Full lifecycle tracking |
| `DispensedItem` | prescription (FK), medicine (FK PROTECT), quantity, dosage_instructions, created_at | Unique together on prescription+medicine |

**Strengths:**
- `display_name` property combines name + strength + form (e.g., "Amoxicillin 500mg (Tablet)")
- Low stock alert via `is_low_stock` property with configurable `min_stock`
- `nearest_expiry` and `has_expired_stock` properties for expiry tracking
- Source tracking for donations vs purchases (6 source types — government, NGO, volunteer, etc.)
- `remaining_qty` on StockEntry enables batch-level tracking
- GinIndex trigram indexes on name, code, batch_number, supplier
- 4-stage dispensing workflow: PENDING → DISPENSING → DISPENSED → COLLECTED
- `unique_together` constraint on DispensedItem prevents duplicate medicine entries per prescription

**Issues Found:**
1. **🔴 Stock deduction doesn't use batch FIFO** — When dispensing, `pharmacy_dispense` deducts from `Medicine.stock` directly but does NOT deduct from `StockEntry.remaining_qty`. This means `remaining_qty` will drift out of sync with actual stock over time. The FIFO batch tracking is essentially broken.
2. **🟡 No reorder point / purchase order system** — Low stock alerts exist but there's no workflow to create purchase orders when stock is low.
3. **🟡 No medicine interaction/contraindication checking** — Prescriptions are free-text with no structured medicine items from the doctor's side.
4. **🟡 No stock adjustment/waste/disposal model** — No way to record expired stock disposal, breakage, or stock count adjustments.
5. **🟡 No pharmacy report** — Unlike billing (which has `billing_report`), pharmacy has no inventory or dispensing reports.
6. **🟡 No selling price on Medicine** — Only `unit_price` on StockEntry (purchase cost). No selling/dispensing price to integrate with billing.

### 2.2 Views (`pharmacy/views.py`) — ✅ Good (with issues)

**Implemented views (12 total):**
| View | Method | Auth | Notes |
|---|---|---|---|
| `pharmacy_dashboard` | GET | `@login_required` | Date-filtered prescription list |
| `prescription_create` | GET/POST | `@login_required` | Create/update prescription (DUPLICATED!) |
| `pharmacy_dispense` | GET/POST | `@login_required` | Dispense medicines from prescription |
| `medicine_list` | GET | `@login_required` | With search, filter (low_stock, expired, inactive), pagination |
| `medicine_add` | GET/POST | `@login_required` | Add medicine |
| `medicine_edit` | GET/POST | `@login_required` | Edit medicine |
| `medicine_delete` | GET/POST | `@login_required` | Delete with protection |
| `stock_entry_list` | GET | `@login_required` | With search, expired/expiring alerts, pagination |
| `stock_entry_add` | GET/POST | `@login_required` | Add stock with source tracking |
| `stock_entry_edit` | GET/POST | `@login_required` | Edit with proportional qty adjustment |
| `stock_entry_delete` | GET/POST | `@login_required` | Delete with stock rollback |

**Strengths:**
- Good medicine search with multiple filter types (low stock, expired, inactive)
- Pagination on medicine_list and stock_entry_list (50 per page)
- Smart stock adjustment on edit (proportional remaining_qty)
- Stock rollback on delete
- Dispensing form with stock restore → clear → re-create workflow
- Visit action logging via `log_visit_action()`

**Issues Found:**
1. **🔴 `prescription_create` is DEFINED TWICE** in views.py (lines ~10-40 and again ~55-95). The second definition overwrites the first. Both are identical. This is a code quality issue.
2. **🔴 No permission checks** — All views only use `@login_required`. Any logged-in user can manage medicines, stock, and dispense.
3. **🔴 Race condition in dispensing** — Stock restore + delete + re-create is not atomic. Concurrent requests could corrupt stock levels. Should use `transaction.atomic()`.
4. **🟡 No validation on stock_entry_add** — `int(request.POST.get('quantity', 0))` can throw ValueError on non-numeric input.
5. **🟡 No forms.py** — Same as billing — all validation is manual in views.

### 2.3 URLs (`pharmacy/urls.py`) — ✅ Good
- 12 URL patterns, well-organized
- Clear naming convention

### 2.4 Admin (`pharmacy/admin.py`) — ✅ Good
- All models registered
- `list_editable` for quick stock updates
- DispensedItem inline on Prescription
- Date hierarchy on StockEntry

### 2.5 Templates (9 files) — ✅ Good
- Professional prescription form mimicking paper clinic forms
- Dynamic medicine row add/remove in dispensing form
- Real-time stock display when selecting medicines
- Expired stock and expiring-soon alerts on stock entry list
- Pagination on list views
- Consistent Bootstrap 5 styling with i18n

### 2.6 Tests (`pharmacy/tests.py`) — ❌ Empty
- No unit tests

---

## 3. APPOINTMENTS APP — ❌ NOT IMPLEMENTED

### 3.1 Current State
All files contain only Django boilerplate:

| File | Content |
|---|---|
| `models.py` | `from django.db import models` + comment |
| `views.py` | `from django.shortcuts import render` + comment |
| `admin.py` | `from django.contrib import admin` + comment |
| `apps.py` | Standard AppConfig |
| `tests.py` | Empty TestCase |
| `urls.py` | **Does not exist** |
| Templates | **None exist** |

### 3.2 What a Professional Clinic Needs

A complete appointments module should include:

**Models needed:**
- `Appointment` — patient, doctor, date/time, duration, status (scheduled/confirmed/cancelled/completed/no-show), appointment_type, notes
- `AppointmentSlot` / `DoctorSchedule` — doctor availability, working hours, break times
- `AppointmentType` — consultation, follow-up, procedure, vaccination, etc.
- `WaitingList` — for walk-ins or overbooked slots

**Views needed:**
- Appointment scheduling (create/edit/cancel)
- Calendar view (daily/weekly for doctors)
- Patient appointment history
- Doctor schedule management
- SMS/notification reminders (optional)
- Walk-in queue integration (the system already has `DailyQueue` in medical_records)
- Dashboard with today's appointments

**Note:** The existing system uses `Visit` + `DailyQueue` in the medical_records app for walk-in patient flow. The appointments app was likely intended for pre-scheduled/future appointments, which is completely missing.

---

## 4. CROSS-CUTTING ISSUES

### 4.1 Security Issues
| Severity | Issue | Location |
|---|---|---|
| 🔴 HIGH | No RBAC on billing views (except 1 API) | billing/views.py |
| 🔴 HIGH | No RBAC on any pharmacy view | pharmacy/views.py |
| 🟡 MEDIUM | No form validation (raw POST parsing) | billing & pharmacy views |
| 🟡 MEDIUM | No rate limiting on AJAX APIs | billing/views.py |

### 4.2 Code Quality Issues
| Severity | Issue | Location |
|---|---|---|
| 🔴 HIGH | Duplicate function definition `prescription_create` | pharmacy/views.py |
| 🟡 MEDIUM | Duplicate invoice creation logic | billing/views.py |
| 🟡 MEDIUM | No Django Forms/ModelForms anywhere | Both apps |
| 🟡 MEDIUM | No unit tests | Both apps |
| 🟢 LOW | Redundant `Q` import | billing/views.py |

### 4.3 Data Integrity Issues
| Severity | Issue | Location |
|---|---|---|
| 🔴 HIGH | StockEntry.remaining_qty never updated on dispensing | pharmacy/views.py |
| 🟡 MEDIUM | No atomic transactions on multi-step operations | pharmacy/views.py (dispense) |
| 🟡 MEDIUM | Overpayment not prevented | billing/views.py |

---

## 5. RECOMMENDATIONS

### Critical (Must Fix)
1. **Implement the appointments app** — It's registered in INSTALLED_APPS but completely empty
2. **Fix pharmacy stock FIFO** — Dispensing must deduct from `StockEntry.remaining_qty` using FIFO (oldest batch first)
3. **Remove duplicate `prescription_create`** in pharmacy/views.py
4. **Add `@permission_required` decorators** to all billing and pharmacy views
5. **Wrap dispensing operations in `transaction.atomic()`**

### High Priority
6. **Create Django Forms** for invoice creation, payment recording, medicine management, and stock entry
7. **Add invoice edit and cancel functionality**
8. **Add a refund/credit note model and workflow**
9. **Add pharmacy reports** (dispensing report, stock movement, expiry report)
10. **Write unit tests** for both apps (invoice calculation, stock management, payment flow)

### Medium Priority
11. **Add proper pagination** to billing dashboard and reports (replace hard limits)
12. **Add search to billing dashboard** (by patient name, invoice number)
13. **Add tax/VAT support** to billing (as per models.md spec)
14. **Add stock adjustment model** for waste, disposal, and stock counts
15. **Integrate pharmacy dispensing with billing** (auto-create invoice items for dispensed medicines)
16. **Add CSV/PDF export** for reports (the `can_export_invoices` permission exists but export isn't implemented)

### Nice to Have
17. Add insurance/third-party payer support
18. Add medicine interaction warnings
19. Add barcode scanning for medicines
20. Add SMS appointment reminders (when appointments are implemented)
21. Add aging report for unpaid invoices

---

## 6. FILES AUDITED

### Billing App
- `D:\pasient_system\backend\billing\models.py` (7,598 bytes)
- `D:\pasient_system\backend\billing\views.py` (17,507 bytes)
- `D:\pasient_system\backend\billing\urls.py` (1,680 bytes)
- `D:\pasient_system\backend\billing\admin.py` (1,298 bytes)
- `D:\pasient_system\backend\billing\apps.py` (152 bytes)
- `D:\pasient_system\backend\billing\tests.py` (63 bytes — empty)
- 11 templates in `D:\pasient_system\backend\templates\billing\`

### Pharmacy App
- `D:\pasient_system\backend\pharmacy\models.py` (8,667 bytes)
- `D:\pasient_system\backend\pharmacy\views.py` (16,249 bytes)
- `D:\pasient_system\backend\pharmacy\urls.py` (1,005 bytes)
- `D:\pasient_system\backend\pharmacy\admin.py` (1,373 bytes)
- `D:\pasient_system\backend\pharmacy\apps.py` (154 bytes)
- `D:\pasient_system\backend\pharmacy\tests.py` (63 bytes — empty)
- 9 templates in `D:\pasient_system\backend\templates\pharmacy\`

### Appointments App
- `D:\pasient_system\backend\appointments\models.py` (60 bytes — empty)
- `D:\pasient_system\backend\appointments\views.py` (66 bytes — empty)
- `D:\pasient_system\backend\appointments\admin.py` (66 bytes — empty)
- `D:\pasient_system\backend\appointments\apps.py` (162 bytes)
- `D:\pasient_system\backend\appointments\tests.py` (63 bytes — empty)
- No urls.py, no templates
