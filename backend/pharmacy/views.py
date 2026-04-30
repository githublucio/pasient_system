from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Q

from medical_records.models import Visit
from .models import Prescription, Medicine, DispensedItem, StockEntry

@login_required
def prescription_create(request, visit_uuid):
    visit = get_object_or_404(Visit, uuid=visit_uuid)
    
    if request.method == 'POST':
        has_allergy = request.POST.get('has_allergy', 'LA_IHA')
        allergy_medicine = request.POST.get('allergy_medicine', '')
        prescription_text = request.POST.get('prescription_text', '')
        
        prescription, created = Prescription.objects.get_or_create(
            visit=visit,
            defaults={
                'doctor': request.user,
                'has_allergy': has_allergy,
                'allergy_medicine': allergy_medicine,
                'prescription_text': prescription_text,
            }
        )
        
        if not created:
            prescription.has_allergy = has_allergy
            prescription.allergy_medicine = allergy_medicine
            prescription.prescription_text = prescription_text
            prescription.doctor = request.user
            prescription.save()
            
        from medical_records.utils import log_visit_action
        log_visit_action(visit, 'PRESCRIPTION', request.user)
        messages.success(request, _("Pharmacy Prescription saved successfully."))
        return redirect('perform_examination', visit_uuid=visit.uuid)
        
    try:
        existing_prescription = visit.prescription
    except Prescription.DoesNotExist:
        existing_prescription = None
    
    return render(request, 'pharmacy/prescription_form.html', {
        'visit': visit,
        'existing_prescription': existing_prescription,
    })

@login_required
def pharmacy_dashboard(request):
    date_str = request.GET.get('date', '')
    if date_str:
        try:
            from datetime import datetime
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            filter_date = timezone.localdate()
    else:
        filter_date = timezone.localdate()

    prescriptions = Prescription.objects.filter(
        date_created__date=filter_date
    ).select_related('visit__patient', 'doctor').prefetch_related('dispensed_items__medicine').order_by('-date_created')

    # ISOLATION: Filter prescriptions by department room
    if not request.user.is_superuser:
        if hasattr(request.user, 'staff_profile') and request.user.staff_profile.department:
            user_dept = request.user.staff_profile.department.code.upper()
            if user_dept in ['HIV', 'AIDS']:
                prescriptions = prescriptions.filter(visit__current_room__code__in=['HIV', 'AIDS'])
            elif user_dept == 'TB':
                prescriptions = prescriptions.filter(visit__current_room__code='TB')
            elif user_dept == 'DENTAL':
                prescriptions = prescriptions.filter(visit__current_room__code='DENTAL')
            else:
                prescriptions = prescriptions.exclude(visit__current_room__code__in=['HIV', 'AIDS', 'TB'])
        else:
            prescriptions = prescriptions.exclude(visit__current_room__code__in=['HIV', 'AIDS', 'TB'])

    pending_count = prescriptions.exclude(dispensing_status__in=['DISPENSED', 'COLLECTED']).count()
    dispensed_count = prescriptions.filter(dispensing_status__in=['DISPENSED', 'COLLECTED']).count()

    return render(request, 'pharmacy/dashboard.html', {
        'prescriptions': prescriptions,
        'filter_date': filter_date,
        'stats': {
            'pending': pending_count,
            'dispensed': dispensed_count,
            'total': prescriptions.count(),
        }
    })


@login_required
def pharmacy_dispense(request, prescription_uuid):
    prescription = get_object_or_404(Prescription, uuid=prescription_uuid)
    
    if request.method == 'POST':
        dispensing_status = request.POST.get('dispensing_status', 'PENDING')
        dispensing_notes = request.POST.get('dispensing_notes', '')
        
        prescription.dispensing_status = dispensing_status
        prescription.dispensing_notes = dispensing_notes
        
        if dispensing_status in ['DISPENSED', 'COLLECTED']:
            prescription.dispensed_by = request.user
            prescription.dispensed_at = timezone.now()
        
        prescription.save()
        
        # Process dispensed items
        medicine_ids = request.POST.getlist('medicine_id')
        quantities = request.POST.getlist('quantity')
        dosages = request.POST.getlist('dosage_instructions')
        
        # Clear old items and re-create
        old_items = list(prescription.dispensed_items.all())
        
        # Restore stock from old items before clearing
        for old_item in old_items:
            old_item.medicine.stock += old_item.quantity
            old_item.medicine.save()
        prescription.dispensed_items.all().delete()
        
        # Create new items and deduct stock
        for med_id, qty, dosage in zip(medicine_ids, quantities, dosages):
            if med_id and qty:
                try:
                    qty_int = int(qty)
                    if qty_int > 0:
                        medicine = Medicine.objects.get(id=med_id)
                        DispensedItem.objects.create(
                            prescription=prescription,
                            medicine=medicine,
                            quantity=qty_int,
                            dosage_instructions=dosage,
                        )
                        medicine.stock = max(0, medicine.stock - qty_int)
                        medicine.save()
                        remaining_to_deduct = qty_int
                        stock_entries = StockEntry.objects.filter(
                            medicine=medicine, remaining_qty__gt=0
                        ).order_by('expiry_date', 'purchase_date')
                        for entry in stock_entries:
                            if remaining_to_deduct <= 0:
                                break
                            deduct = min(entry.remaining_qty, remaining_to_deduct)
                            entry.remaining_qty -= deduct
                            entry.save()
                            remaining_to_deduct -= deduct
                except (ValueError, Medicine.DoesNotExist):
                    pass
        
        from medical_records.utils import log_visit_action
        log_visit_action(prescription.visit, 'DISPENSED', request.user)
        messages.success(request, _("Prescription dispensing updated successfully."))
        return redirect('pharmacy_dashboard')
    
    # ISOLATION: Filter medicine based on department
    department_code = 'GENERAL'
    if prescription.visit.current_room:
        room_code = prescription.visit.current_room.code.upper()
        if room_code in ['HIV', 'AIDS']:
            department_code = 'HIV'
        elif room_code == 'TB':
            department_code = 'TB'
        elif room_code == 'DENTAL':
            department_code = 'DENTAL'

    all_medicines = Medicine.objects.filter(
        is_active=True, 
        department_category=department_code
    ).order_by('name')

    existing_items = prescription.dispensed_items.select_related('medicine').all()
    
    from .utils import check_drug_interactions
    medicine_names = [item.medicine.name for item in existing_items]
    interaction_warnings = check_drug_interactions(medicine_names)
    
    return render(request, 'pharmacy/dispense_form.html', {
        'prescription': prescription,
        'all_medicines': all_medicines,
        'existing_items': existing_items,
        'interaction_warnings': interaction_warnings,
    })


# =============================================
# Medicine CRUD
# =============================================

@login_required
def medicine_list(request):
    q = request.GET.get('q', '')
    filter_type = request.GET.get('filter', '')
    medicines = Medicine.objects.all()
    
    # ISOLATION: Non-admin staff only see their department's stock
    if not request.user.is_superuser:
        if hasattr(request.user, 'staff_profile') and request.user.staff_profile.department:
            user_dept = request.user.staff_profile.department.code.upper()
            if user_dept in ['HIV', 'AIDS']:
                medicines = medicines.filter(department_category='HIV')
            elif user_dept == 'TB':
                medicines = medicines.filter(department_category='TB')
            elif user_dept == 'DENTAL':
                medicines = medicines.filter(department_category='DENTAL')
            else:
                medicines = medicines.filter(department_category='GENERAL')
        else:
            medicines = medicines.filter(department_category='GENERAL')

    if q:
        medicines = medicines.filter(Q(name__icontains=q) | Q(code__icontains=q))

    if filter_type == 'low_stock':
        from django.db.models import F
        medicines = medicines.filter(stock__lte=F('min_stock'))
    elif filter_type == 'expired':
        today = timezone.localdate()
        expired_med_ids = StockEntry.objects.filter(
            expiry_date__lt=today, remaining_qty__gt=0
        ).values_list('medicine_id', flat=True)
        medicines = medicines.filter(id__in=expired_med_ids)
    elif filter_type == 'inactive':
        medicines = medicines.filter(is_active=False)

    from django.core.paginator import Paginator
    paginator = Paginator(medicines, 50)
    page = request.GET.get('page', 1)
    medicines = paginator.get_page(page)

    return render(request, 'pharmacy/medicine_list.html', {
        'medicines': medicines,
        'query': q,
        'filter_type': filter_type,
    })


@login_required
def medicine_add(request):
    # Generate next code
    last_med = Medicine.objects.filter(code__startswith='MED-').order_by('-code').first()
    if last_med:
        try:
            # Extract number from MED-XXXX
            last_code = last_med.code
            number_part = last_code.split('-')[1]
            next_number = int(number_part) + 1
            suggested_code = f"MED-{next_number:04d}"
        except (IndexError, ValueError):
            suggested_code = "MED-0001"
    else:
        suggested_code = "MED-0001"

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', suggested_code).strip() or suggested_code
        unit = request.POST.get('unit', 'TABLET')
        min_stock = int(request.POST.get('min_stock', 10))
        description = request.POST.get('description', '')
        strength = request.POST.get('strength', '').strip() or None
        form_type = request.POST.get('form', 'TABLET')

        # Double check if code exists
        if Medicine.objects.filter(code=code).exists():
            # If exists, try to generate a fresh one
            last_med = Medicine.objects.filter(code__startswith='MED-').order_by('-code').first()
            if last_med:
                next_number = int(last_med.code.split('-')[1]) + 1
                code = f"MED-{next_number:04d}"

        try:
            Medicine.objects.create(
                name=name, strength=strength, form=form_type,
                code=code, unit=unit,
                min_stock=min_stock, description=description,
            )
            messages.success(request, _("Medicine added successfully with code %(code)s.") % {'code': code})
            return redirect('medicine_list')
        except Exception as e:
            messages.error(request, _("Error adding medicine: %(error)s") % {'error': str(e)})

    return render(request, 'pharmacy/medicine_form.html', {
        'title': _('Add New Medicine'),
        'medicine': None,
        'suggested_code': suggested_code,
        'unit_choices': Medicine.UNIT_CHOICES,
        'form_choices': Medicine.FORM_CHOICES,
    })


@login_required
def medicine_edit(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        medicine.name = request.POST.get('name', '').strip()
        medicine.strength = request.POST.get('strength', '').strip() or None
        medicine.form = request.POST.get('form', 'TABLET')
        medicine.code = request.POST.get('code', '').strip() or None
        medicine.unit = request.POST.get('unit', 'TABLET')
        medicine.min_stock = int(request.POST.get('min_stock', 10))
        medicine.description = request.POST.get('description', '')
        medicine.is_active = request.POST.get('is_active') == 'on'
        medicine.save()
        messages.success(request, _("Medicine updated successfully."))
        return redirect('medicine_list')

    return render(request, 'pharmacy/medicine_form.html', {
        'title': _('Edit Medicine'),
        'medicine': medicine,
        'unit_choices': Medicine.UNIT_CHOICES,
        'form_choices': Medicine.FORM_CHOICES,
    })


@login_required
def medicine_delete(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        try:
            medicine.delete()
            messages.success(request, _("Medicine deleted."))
        except Exception:
            messages.error(request, _("Cannot delete this medicine. It has been used in dispensing records."))
        return redirect('medicine_list')

    return render(request, 'pharmacy/medicine_confirm_delete.html', {
        'medicine': medicine,
    })


# =============================================
# Stock Entry (Obat Masuk) CRUD
# =============================================

@login_required
def stock_entry_list(request):
    q = request.GET.get('q', '')
    entries = StockEntry.objects.select_related('medicine', 'created_by').all()
    
    # ISOLATION: Non-admin staff only see their department's stock entries
    if not request.user.is_superuser:
        if hasattr(request.user, 'staff_profile') and request.user.staff_profile.department:
            user_dept = request.user.staff_profile.department.code.upper()
            if user_dept in ['HIV', 'AIDS']:
                entries = entries.filter(medicine__department_category='HIV')
            elif user_dept == 'TB':
                entries = entries.filter(medicine__department_category='TB')
            elif user_dept == 'DENTAL':
                entries = entries.filter(medicine__department_category='DENTAL')
            else:
                entries = entries.filter(medicine__department_category='GENERAL')
        else:
            entries = entries.filter(medicine__department_category='GENERAL')

    if q:
        entries = entries.filter(
            Q(medicine__name__icontains=q) | Q(batch_number__icontains=q) | Q(supplier__icontains=q)
        )

    today = timezone.localdate()
    
    expired_qs = StockEntry.objects.filter(expiry_date__lt=today, remaining_qty__gt=0)
    expiring_soon_qs = StockEntry.objects.filter(
        expiry_date__gte=today,
        expiry_date__lte=today + timezone.timedelta(days=90),
        remaining_qty__gt=0
    )

    if not request.user.is_superuser:
        if hasattr(request.user, 'staff_profile') and request.user.staff_profile.department:
            user_dept = request.user.staff_profile.department.code.upper()
            if user_dept in ['HIV', 'AIDS']:
                expired_qs = expired_qs.filter(medicine__department_category='HIV')
                expiring_soon_qs = expiring_soon_qs.filter(medicine__department_category='HIV')
            elif user_dept == 'TB':
                expired_qs = expired_qs.filter(medicine__department_category='TB')
                expiring_soon_qs = expiring_soon_qs.filter(medicine__department_category='TB')
            elif user_dept == 'DENTAL':
                expired_qs = expired_qs.filter(medicine__department_category='DENTAL')
                expiring_soon_qs = expiring_soon_qs.filter(medicine__department_category='DENTAL')
            else:
                expired_qs = expired_qs.filter(medicine__department_category='GENERAL')
                expiring_soon_qs = expiring_soon_qs.filter(medicine__department_category='GENERAL')
        else:
            expired_qs = expired_qs.filter(medicine__department_category='GENERAL')
            expiring_soon_qs = expiring_soon_qs.filter(medicine__department_category='GENERAL')

    expired_count = expired_qs.count()
    expiring_soon_count = expiring_soon_qs.count()

    from django.core.paginator import Paginator
    paginator = Paginator(entries, 50)
    page = request.GET.get('page', 1)
    entries = paginator.get_page(page)

    return render(request, 'pharmacy/stock_entry_list.html', {
        'entries': entries,
        'query': q,
        'expired_count': expired_count,
        'expiring_soon_count': expiring_soon_count,
    })


@login_required
def stock_entry_add(request):
    if request.method == 'POST':
        medicine_id = request.POST.get('medicine')
        quantity = int(request.POST.get('quantity', 0))
        expiry_date = request.POST.get('expiry_date') or None
        batch_number = request.POST.get('batch_number', '').strip() or None
        supplier = request.POST.get('supplier', '').strip() or None
        purchase_date = request.POST.get('purchase_date')
        unit_price = request.POST.get('unit_price', 0) or 0
        notes = request.POST.get('notes', '')

        medicine = get_object_or_404(Medicine, pk=medicine_id)

        source_type = request.POST.get('source_type', 'PURCHASE')
        donor_name = request.POST.get('donor_name', '').strip() or None

        StockEntry.objects.create(
            medicine=medicine,
            source_type=source_type,
            donor_name=donor_name,
            quantity=quantity,
            remaining_qty=quantity,
            expiry_date=expiry_date,
            batch_number=batch_number,
            supplier=supplier,
            purchase_date=purchase_date,
            unit_price=unit_price,
            notes=notes,
            created_by=request.user,
        )

        # Update medicine stock
        medicine.stock += quantity
        medicine.save()

        messages.success(request, _("Stock entry added. %(name)s stock updated to %(stock)s.") % {
            'name': medicine.name, 'stock': medicine.stock
        })
        return redirect('stock_entry_list')

    # ISOLATION
    all_medicines = Medicine.objects.filter(is_active=True).order_by('name')
    if not request.user.is_superuser:
        if hasattr(request.user, 'staff_profile') and request.user.staff_profile.department:
            user_dept = request.user.staff_profile.department.code.upper()
            if user_dept in ['HIV', 'AIDS']:
                all_medicines = all_medicines.filter(department_category='HIV')
            elif user_dept == 'TB':
                all_medicines = all_medicines.filter(department_category='TB')
            elif user_dept == 'DENTAL':
                all_medicines = all_medicines.filter(department_category='DENTAL')
            else:
                all_medicines = all_medicines.filter(department_category='GENERAL')
        else:
            all_medicines = all_medicines.filter(department_category='GENERAL')
    return render(request, 'pharmacy/stock_entry_form.html', {
        'title': _('Add Stock Entry (Obat Masuk)'),
        'entry': None,
        'all_medicines': all_medicines,
        'source_choices': StockEntry.SOURCE_CHOICES,
    })


@login_required
def stock_entry_edit(request, pk):
    entry = get_object_or_404(StockEntry, pk=pk)
    old_quantity = entry.quantity

    if request.method == 'POST':
        new_quantity = int(request.POST.get('quantity', 0))
        entry.source_type = request.POST.get('source_type', entry.source_type)
        entry.donor_name = request.POST.get('donor_name', '').strip() or None
        entry.expiry_date = request.POST.get('expiry_date') or None
        entry.batch_number = request.POST.get('batch_number', '').strip() or None
        entry.supplier = request.POST.get('supplier', '').strip() or None
        entry.purchase_date = request.POST.get('purchase_date')
        entry.unit_price = request.POST.get('unit_price', 0) or 0
        entry.notes = request.POST.get('notes', '')

        # Adjust remaining_qty proportionally
        diff = new_quantity - old_quantity
        entry.quantity = new_quantity
        entry.remaining_qty = max(0, entry.remaining_qty + diff)
        entry.save()

        # Adjust medicine stock
        entry.medicine.stock = max(0, entry.medicine.stock + diff)
        entry.medicine.save()

        messages.success(request, _("Stock entry updated."))
        return redirect('stock_entry_list')

    # ISOLATION
    all_medicines = Medicine.objects.filter(is_active=True).order_by('name')
    if not request.user.is_superuser:
        if hasattr(request.user, 'staff_profile') and request.user.staff_profile.department:
            user_dept = request.user.staff_profile.department.code.upper()
            if user_dept in ['HIV', 'AIDS']:
                all_medicines = all_medicines.filter(department_category='HIV')
            elif user_dept == 'TB':
                all_medicines = all_medicines.filter(department_category='TB')
            elif user_dept == 'DENTAL':
                all_medicines = all_medicines.filter(department_category='DENTAL')
            else:
                all_medicines = all_medicines.filter(department_category='GENERAL')
        else:
            all_medicines = all_medicines.filter(department_category='GENERAL')
    return render(request, 'pharmacy/stock_entry_form.html', {
        'title': _('Edit Stock Entry'),
        'entry': entry,
        'all_medicines': all_medicines,
        'source_choices': StockEntry.SOURCE_CHOICES,
    })


@login_required
def stock_entry_delete(request, pk):
    entry = get_object_or_404(StockEntry, pk=pk)
    if request.method == 'POST':
        entry.medicine.stock = max(0, entry.medicine.stock - entry.remaining_qty)
        entry.medicine.save()
        entry.delete()
        messages.success(request, _("Stock entry deleted. Medicine stock adjusted."))
        return redirect('stock_entry_list')

    return render(request, 'pharmacy/stock_entry_confirm_delete.html', {
        'entry': entry,
    })
