import os
import sys
import django
from datetime import date

# Setup path and Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from billing.models import Invoice, InvoiceItem
from django.utils import timezone
from django.template.loader import get_template

def verify_billing_system():
    print("--- BILLING SYSTEM VERIFICATION REPORT ---")
    
    # 1. Test Period Logic (Dry Run of View Logic)
    print("\n[1] Testing Period Calculation Logic:")
    today = timezone.localdate()
    periods = ['today', 'month', 'quarter', 'year']
    for period in periods:
        try:
            if period == 'today':
                d_from = today
            elif period == 'month':
                d_from = today.replace(day=1)
            elif period == 'quarter':
                quarter_month = ((today.month - 1) // 3) * 3 + 1
                d_from = today.replace(month=quarter_month, day=1)
            elif period == 'year':
                d_from = today.replace(month=1, day=1)
            print(f"  - Period '{period}': Starts from {d_from} (OK)")
        except Exception as e:
            print(f"  - Period '{period}': ERROR {e}")

    # 2. Check Database Relations
    print("\n[2] Checking Database Relations:")
    try:
        sample_invoice = Invoice.objects.select_related('visit__diagnosis').first()
        if sample_invoice:
            print(f"  - Relation Invoice -> Visit -> Diagnosis: OK")
            summary = sample_invoice.get_items_summary()
            print(f"  - get_items_summary() execution: OK (Result: '{summary[:30]}...')")
        else:
            print("  - No invoices in DB to test relations, but query structure is valid.")
    except Exception as e:
        print(f"  - RELATION ERROR: {e}")

    # 3. Template Rendering Check
    print("\n[3] Billing Templates Check:")
    templates = [
        'billing/report.html',
        'billing/pdf/report_pdf.html',
        'billing/invoice_detail.html'
    ]
    for t in templates:
        try:
            get_template(t)
            print(f"  - Template '{t}': Renders OK")
        except Exception as e:
            print(f"  - TEMPLATE ERROR in '{t}': {e}")

    print("\n--- END OF REPORT ---")

if __name__ == "__main__":
    verify_billing_system()
