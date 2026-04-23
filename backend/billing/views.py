from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.translation import gettext as _
from django.utils import timezone
from django.db.models import Sum, Q, F, Count
from django.http import JsonResponse, HttpResponse
from decimal import Decimal, InvalidOperation

from .models import ServiceCategory, ServicePrice, Invoice, InvoiceItem, Payment
from patients.models import Patient
from medical_records.models import Visit


# =============================================
# Billing Dashboard
# =============================================

@login_required
def billing_dashboard(request):
    date_str = request.GET.get('date', '')
    if date_str:
        try:
            from datetime import datetime
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            filter_date = timezone.localdate()
    else:
        filter_date = timezone.localdate()

    invoices = Invoice.objects.visible_to(request.user).filter(
        created_at__date=filter_date
    ).select_related('patient', 'visit', 'created_by').prefetch_related(
        'items__category', 'items__service__category'
    ).order_by('-created_at')[:200]

    today_stats = Invoice.objects.filter(created_at__date=filter_date).aggregate(
        total_invoices=Count('uuid'),
        total_billed=Sum('total_amount'),
        total_paid=Sum('amount_paid'),
    )

    unpaid_count = Invoice.objects.visible_to(request.user).filter(
        created_at__date=filter_date, status='UNPAID'
    ).count()

    return render(request, 'billing/dashboard.html', {
        'invoices': invoices,
        'filter_date': filter_date,
        'total_invoices': today_stats['total_invoices'] or 0,
        'total_billed': today_stats['total_billed'] or Decimal('0.00'),
        'total_paid': today_stats['total_paid'] or Decimal('0.00'),
        'unpaid_count': unpaid_count,
    })


# =============================================
# Create Invoice
# =============================================

@login_required
def invoice_create(request):
    if request.method == 'POST':
        patient_uuid = request.POST.get('patient')
        visit_uuid = request.POST.get('visit') or None
        discount = Decimal(request.POST.get('discount', '0') or '0')
        notes = request.POST.get('notes', '')

        patient = get_object_or_404(Patient.objects.visible_to(request.user), uuid=patient_uuid)
        visit = None
        if visit_uuid:
            visit = Visit.objects.filter(uuid=visit_uuid).first()
            if visit and hasattr(visit, 'invoice'):
                messages.warning(request, _("An invoice already exists for this visit."))
                return redirect('invoice_detail', uuid=visit.invoice.uuid)

        invoice = Invoice.objects.create(
            invoice_number=Invoice.generate_invoice_number(),
            patient=patient,
            visit=visit,
            discount=discount,
            notes=notes,
            created_by=request.user,
        )

        descriptions = request.POST.getlist('item_description')
        quantities = request.POST.getlist('item_quantity')
        prices = request.POST.getlist('item_price')
        service_ids = request.POST.getlist('item_service_id')
        category_ids = request.POST.getlist('item_category_id')

        for i in range(len(descriptions)):
            desc = descriptions[i].strip()
            if not desc:
                continue
            try:
                qty = int(quantities[i]) if i < len(quantities) else 1
                price = Decimal(prices[i]) if i < len(prices) else Decimal('0')
            except (ValueError, InvalidOperation):
                continue

            svc = None
            cat = None
            if i < len(service_ids) and service_ids[i]:
                svc = ServicePrice.objects.filter(pk=service_ids[i]).first()
                if svc:
                    cat = svc.category
            
            if not cat and i < len(category_ids) and category_ids[i]:
                cat = ServiceCategory.objects.filter(pk=category_ids[i]).first()

            # TB Exception: Set price to 0 for TB patients (global check)
            is_tb = False
            if patient.is_tb_patient:
                is_tb = True
            elif visit and visit.current_room and visit.current_room.code == 'TB':
                is_tb = True
            elif visit and (visit.diagnosis and 'A15' <= visit.diagnosis.code.upper() <= 'A19'):
                is_tb = True

            if is_tb:
                price = Decimal('0.00')

            InvoiceItem.objects.create(
                invoice=invoice,
                service=svc,
                category=cat,
                description=desc,
                quantity=max(qty, 1),
                unit_price=price,
            )

        invoice.recalculate()
        messages.success(request, _("Invoice %(num)s created successfully.") % {'num': invoice.invoice_number})
        return redirect('invoice_detail', uuid=invoice.uuid)

    categories = ServiceCategory.objects.filter(is_active=True).prefetch_related(
        'services'
    )

    return render(request, 'billing/invoice_form.html', {
        'title': _('Create New Invoice'),
        'categories': categories,
        'editing': False,
    })


@login_required
def invoice_create_for_visit(request, visit_uuid):
    visit = get_object_or_404(Visit, uuid=visit_uuid)

    existing = Invoice.objects.visible_to(request.user).filter(visit=visit).first()
    if existing:
        return redirect('invoice_detail', uuid=existing.uuid)

    if request.method == 'POST':
        discount = Decimal(request.POST.get('discount', '0') or '0')
        notes = request.POST.get('notes', '')

        invoice = Invoice.objects.create(
            invoice_number=Invoice.generate_invoice_number(),
            patient=visit.patient,
            visit=visit,
            discount=discount,
            notes=notes,
            created_by=request.user,
        )

        descriptions = request.POST.getlist('item_description')
        quantities = request.POST.getlist('item_quantity')
        prices = request.POST.getlist('item_price')
        service_ids = request.POST.getlist('item_service_id')
        category_ids = request.POST.getlist('item_category_id')

        for i in range(len(descriptions)):
            desc = descriptions[i].strip()
            if not desc:
                continue
            try:
                qty = int(quantities[i]) if i < len(quantities) else 1
                price = Decimal(prices[i]) if i < len(prices) else Decimal('0')
            except (ValueError, InvalidOperation):
                continue

            svc = None
            cat = None
            if i < len(service_ids) and service_ids[i]:
                svc = ServicePrice.objects.filter(pk=service_ids[i]).first()
                if svc:
                    cat = svc.category

            if not cat and i < len(category_ids) and category_ids[i]:
                cat = ServiceCategory.objects.filter(pk=category_ids[i]).first()

            # TB Exception: If visit is in TB room or patient is tagged as TB patient, set price to 0
            is_tb = False
            if visit and visit.patient.is_tb_patient:
                is_tb = True
            elif visit and visit.current_room and visit.current_room.code == 'TB':
                is_tb = True
            elif visit and (visit.diagnosis and 'A15' <= visit.diagnosis.code.upper() <= 'A19'):
                is_tb = True

            if is_tb:
                price = Decimal('0.00')

            InvoiceItem.objects.create(
                invoice=invoice,
                service=svc,
                category=cat,
                description=desc,
                quantity=max(qty, 1),
                unit_price=price,
            )

        invoice.recalculate()
        messages.success(request, _("Invoice %(num)s created successfully.") % {'num': invoice.invoice_number})
        return redirect('invoice_detail', uuid=invoice.uuid)

    categories = ServiceCategory.objects.filter(is_active=True).prefetch_related('services')

    return render(request, 'billing/invoice_form.html', {
        'title': _('Create Invoice for Visit'),
        'visit': visit,
        'patient': visit.patient,
        'categories': categories,
        'editing': False,
    })


# =============================================
# Invoice Detail & Print
# =============================================

@login_required
def invoice_detail(request, uuid):
    invoice = get_object_or_404(
        Invoice.objects.visible_to(request.user).select_related('patient', 'visit', 'created_by').prefetch_related(
            'items__service', 'items__service__category', 'items__category', 'payments__received_by'
        ),
        uuid=uuid
    )
    return render(request, 'billing/invoice_detail.html', {
        'invoice': invoice,
    })


@login_required
def invoice_print(request, uuid):
    invoice = get_object_or_404(
        Invoice.objects.visible_to(request.user).select_related('patient', 'visit', 'created_by').prefetch_related('items__service'),
        uuid=uuid
    )
    return render(request, 'billing/invoice_print.html', {
        'invoice': invoice,
    })


# =============================================
# Record Payment
# =============================================

@login_required
def payment_create(request, invoice_uuid):
    invoice = get_object_or_404(
        Invoice.objects.visible_to(request.user).select_related('patient').prefetch_related(
            'items__category', 'items__service__category', 'payments'
        ),
        uuid=invoice_uuid,
    )

    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', '0'))
        except InvalidOperation:
            amount = Decimal('0')
        payment_method = request.POST.get('payment_method', 'CASH')
        reference = request.POST.get('reference', '').strip()
        notes = request.POST.get('notes', '')

        if amount > 0:
            Payment.objects.create(
                invoice=invoice,
                amount=amount,
                payment_method=payment_method,
                reference=reference or None,
                notes=notes,
                received_by=request.user,
            )

            invoice.amount_paid = invoice.payments.aggregate(total=Sum('amount'))['total'] or 0
            invoice.payment_method = payment_method
            invoice.recalculate()

            messages.success(request, _("Payment of $%(amount)s recorded.") % {'amount': amount})
        else:
            messages.error(request, _("Invalid payment amount."))

        return redirect('invoice_detail', uuid=invoice.uuid)

    return render(request, 'billing/payment_form.html', {
        'invoice': invoice,
    })


# =============================================
# Service Price Management (Master Data)
# =============================================

@login_required
def service_category_list(request):
    categories = ServiceCategory.objects.prefetch_related('services').all()
    return render(request, 'billing/service_category_list.html', {
        'categories': categories,
    })


@login_required
def service_category_add(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()
        icon = request.POST.get('icon', 'bi-tag').strip()
        order = int(request.POST.get('order', 0))

        ServiceCategory.objects.create(name=name, code=code, icon=icon, order=order)
        messages.success(request, _("Category added."))
        return redirect('service_category_list')

    return render(request, 'billing/service_category_form.html', {
        'title': _('Add Service Category'),
        'category': None,
    })


@login_required
def service_category_edit(request, pk):
    cat = get_object_or_404(ServiceCategory, pk=pk)
    if request.method == 'POST':
        cat.name = request.POST.get('name', '').strip()
        cat.code = request.POST.get('code', '').strip().upper()
        cat.icon = request.POST.get('icon', 'bi-tag').strip()
        cat.order = int(request.POST.get('order', 0))
        cat.is_active = request.POST.get('is_active') == 'on'
        cat.save()
        messages.success(request, _("Category updated."))
        return redirect('service_category_list')

    return render(request, 'billing/service_category_form.html', {
        'title': _('Edit Service Category'),
        'category': cat,
    })


@login_required
def service_price_add(request, category_pk):
    cat = get_object_or_404(ServiceCategory, pk=category_pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip() or None
        price = Decimal(request.POST.get('price', '0') or '0')
        description = request.POST.get('description', '')

        ServicePrice.objects.create(
            category=cat, name=name, code=code, price=price, description=description,
        )
        messages.success(request, _("Service added."))
        return redirect('service_category_list')

    return render(request, 'billing/service_price_form.html', {
        'title': _('Add Service to %(cat)s') % {'cat': cat.name},
        'category': cat,
        'service': None,
    })


@login_required
def service_price_edit(request, pk):
    svc = get_object_or_404(ServicePrice, pk=pk)
    if request.method == 'POST':
        svc.name = request.POST.get('name', '').strip()
        svc.code = request.POST.get('code', '').strip() or None
        svc.price = Decimal(request.POST.get('price', '0') or '0')
        svc.description = request.POST.get('description', '')
        svc.is_active = request.POST.get('is_active') == 'on'
        svc.save()
        messages.success(request, _("Service updated."))
        return redirect('service_category_list')

    return render(request, 'billing/service_price_form.html', {
        'title': _('Edit Service'),
        'category': svc.category,
        'service': svc,
    })


@login_required
def service_price_delete(request, pk):
    svc = get_object_or_404(ServicePrice, pk=pk)
    if request.method == 'POST':
        svc.delete()
        messages.success(request, _("Service deleted."))
        return redirect('service_category_list')
    return render(request, 'billing/service_price_confirm_delete.html', {'service': svc})


# =============================================
# API: Search patients (for AJAX)
# =============================================

@login_required
def api_search_patients(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)
    from django.db.models import Q
    patients = Patient.objects.visible_to(request.user).filter(
        Q(full_name__icontains=q) | Q(patient_id__icontains=q) | Q(phone_number__icontains=q)
    ).values('uuid', 'patient_id', 'full_name', 'date_of_birth')[:15]
    return JsonResponse(list(patients, ), safe=False)


# =============================================
# API: Load services by category (for JS)
# =============================================

@login_required
def api_services_by_category(request):
    cat_id = request.GET.get('category_id')
    if not cat_id:
        return JsonResponse([], safe=False)
    services = ServicePrice.objects.filter(
        category_id=cat_id, is_active=True
    ).values('id', 'name', 'price', 'code')
    return JsonResponse(list(services), safe=False)

@login_required
@permission_required('billing.view_menu_billing', raise_exception=True)
def api_patient_visits(request, patient_uuid):
    from medical_records.models import Visit
    from django.utils import timezone
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    # Filter visits from last 30 days and EXCLUDE those that already have an invoice
    visits = Visit.objects.visible_to(request.user).filter(
        patient_id=patient_uuid, 
        visit_date__gte=thirty_days_ago
    ).exclude(invoice__isnull=False).order_by('-visit_date')
    
    data = []
    for v in visits:
        data.append({
            'id': str(v.uuid),
            'date': v.visit_date.strftime('%Y-%m-%d %H:%M'),
            'queue': v.queue_number,
            'status': v.get_status_display()
        })
    return JsonResponse(data, safe=False)


# =============================================
# Reports
# =============================================

@login_required
def billing_report(request):
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    category_id = request.GET.get('category', '')
    period = request.GET.get('period', '')

    today = timezone.localdate()
    
    if period == 'today':
        date_from = today.isoformat()
        date_to = today.isoformat()
    elif period == 'month':
        date_from = today.replace(day=1).isoformat()
        date_to = today.isoformat()
    elif period == 'quarter':
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        date_from = today.replace(month=quarter_month, day=1).isoformat()
        date_to = today.isoformat()
    elif period == 'year':
        date_from = today.replace(month=1, day=1).isoformat()
        date_to = today.isoformat()

    if not date_from:
        date_from = today.replace(day=1).isoformat()
    if not date_to:
        date_to = today.isoformat()

    invoices = Invoice.objects.visible_to(request.user).filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).exclude(status='CANCELLED')

    if category_id:
        invoices = invoices.filter(items__service__category_id=category_id).distinct()

    totals = invoices.aggregate(
        total_billed=Sum('total_amount'),
        total_paid=Sum('amount_paid'),
        count=Count('uuid'),
    )

    # Revenue by category
    category_breakdown = InvoiceItem.objects.filter(
        invoice__created_at__date__gte=date_from,
        invoice__created_at__date__lte=date_to,
        invoice__status__in=['PAID', 'PARTIAL'],
    ).values(
        cat_name=F('category__name')
    ).annotate(
        total=Sum(F('quantity') * F('unit_price')),
        item_count=Count('id'),
    ).order_by('-total')

    categories = ServiceCategory.objects.filter(is_active=True)

    # select_related visit__diagnosis for reporting
    invoices = invoices.select_related('patient', 'visit__diagnosis').prefetch_related(
        'items__category', 'items__service__category'
    ).order_by('-created_at')[:200]

    return render(request, 'billing/report.html', {
        'date_from': date_from,
        'date_to': date_to,
        'category_id': category_id,
        'invoices': invoices,
        'total_billed': totals['total_billed'] or Decimal('0.00'),
        'total_paid': totals['total_paid'] or Decimal('0.00'),
        'invoice_count': totals['count'] or 0,
        'category_breakdown': category_breakdown,
        'categories': categories,
    })


@login_required
def patient_billing_history(request, patient_uuid):
    patient = get_object_or_404(Patient.objects.visible_to(request.user), uuid=patient_uuid)
    invoices = Invoice.objects.visible_to(request.user).filter(patient=patient).select_related('visit').prefetch_related(
        'items__category', 'items__service__category', 'payments'
    )

    totals = invoices.exclude(status='CANCELLED').aggregate(
        total_billed=Sum('total_amount'),
        total_paid=Sum('amount_paid'),
    )

    return render(request, 'billing/patient_history.html', {
        'patient': patient,
        'invoices': invoices,
        'total_billed': totals['total_billed'] or Decimal('0.00'),
        'total_paid': totals['total_paid'] or Decimal('0.00'),
    })


@login_required
def invoice_pdf(request, uuid):
    """Generate PDF for a single invoice."""
    invoice = get_object_or_404(
        Invoice.objects.visible_to(request.user).select_related('patient', 'visit', 'created_by').prefetch_related(
            'items__service', 'items__service__category', 'items__category', 'payments__received_by'
        ),
        uuid=uuid
    )
    from clinic_core.pdf_utils import render_to_pdf
    context = {'invoice': invoice}
    pdf = render_to_pdf('billing/pdf/invoice_pdf.html', context)
    if pdf:
        filename = f"Invoice_{invoice.invoice_number}.pdf"
        pdf['Content-Disposition'] = f'inline; filename="{filename}"'
        return pdf
    return HttpResponse("Error generating PDF", status=500)


@login_required
def billing_report_pdf(request):
    """Generate PDF for billing report with date range."""
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    today = timezone.localdate()
    if not date_from:
        date_from = today.replace(day=1).isoformat()
    if not date_to:
        date_to = today.isoformat()

    invoices = Invoice.objects.visible_to(request.user).filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).exclude(status='CANCELLED').select_related('patient', 'visit__diagnosis').prefetch_related(
        'items__category', 'items__service__category'
    ).order_by('-created_at')

    totals = invoices.aggregate(
        total_billed=Sum('total_amount'),
        total_paid=Sum('amount_paid'),
        count=Count('uuid'),
    )

    from clinic_core.pdf_utils import render_to_pdf
    context = {
        'invoices': list(invoices[:200]),
        'date_from': date_from,
        'date_to': date_to,
        'total_billed': totals['total_billed'] or Decimal('0.00'),
        'total_paid': totals['total_paid'] or Decimal('0.00'),
        'invoice_count': totals['count'] or 0,
    }
    pdf = render_to_pdf('billing/pdf/report_pdf.html', context)
    if pdf:
        pdf['Content-Disposition'] = f'inline; filename="Billing_Report_{date_from}_to_{date_to}.pdf"'
        return pdf
    return HttpResponse("Error generating PDF", status=500)
