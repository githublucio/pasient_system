from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q, Max, ProtectedError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import hashlib
from dateutil.relativedelta import relativedelta
from .forms import PatientRegistrationForm
from .models import Patient, Municipio, PostoAdministrativo, Suco, Aldeia, DailyQueue, PatientID
from medical_records.models import Visit

@login_required
@permission_required('patients.add_patient', raise_exception=True)
def register_patient(request):
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            
            # Re-calculate at save time to ensure uniqueness if someone else grabbed the one shown
            patient.patient_id = Patient.generate_next_id()
            patient.save()
            return redirect('patient_dashboard', uuid=patient.uuid)
    else:
        # Pre-calculate for display
        next_id = Patient.generate_next_id()
        form = PatientRegistrationForm(initial={'patient_id': next_id})
    return render(request, 'patients/register.html', {'form': form})

@login_required
@permission_required('patients.add_patient', raise_exception=True)
def hiv_register_patient(request):
    """
    Simplified registration for HIV clinic staff.
    Bypasses registration fee and automatically creates a visit record in the 'HIV' room.
    """
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST, is_hiv=True)
        if form.is_valid():
            patient = form.save(commit=False)
            
            # Re-calculate at save time
            patient.patient_id = Patient.generate_next_id()
            patient.is_hiv_patient = True # Set the HIV flag
            patient.save()
            
            # AUTO-CHECK-IN to HIV ROOM
            from medical_records.models import Room
            hiv_room = Room.objects.filter(code='HIV').first()
            if not hiv_room:
                 # Fallback if room not found (should be handled by admin setup)
                 messages.warning(request, _("Patient registered, but HIV Room not found for automatic check-in."))
                 return redirect('patient_dashboard', uuid=patient.uuid)

            # Get or create today's queue for HIV
            today = timezone.localdate()
            queue, created = DailyQueue.objects.get_or_create(date=today, department='HIV')
            queue_number = queue.get_next_number()

            # Create the Visit
            visit = Visit.objects.create(
                patient=patient,
                queue_number=queue_number,
                status='SCH',
                current_room=hiv_room,
                visit_fee=0.00,
                patient_type='FOUN', # New patient
                checked_in_by=request.user,
            )
            
            from medical_records.utils import log_visit_action
            log_visit_action(visit, 'CHECK_IN', request.user, room=hiv_room)

            messages.success(request, _("Patient registered and added to HIV queue successfully."))
            return redirect('doctor_dashboard')
    else:
        next_id = Patient.generate_next_id()
        form = PatientRegistrationForm(is_hiv=True, initial={'patient_id': next_id})
    
    return render(request, 'patients/register.html', {
        'form': form, 
        'title': _('Register New HIV Patient (Free)'),
        'is_hiv': True
    })

@login_required
@permission_required('patients.change_patient', raise_exception=True)
def edit_patient(request, uuid):
    patient = get_object_or_404(Patient, uuid=uuid)
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            return redirect('patient_dashboard', uuid=patient.uuid)
    else:
        form = PatientRegistrationForm(instance=patient)
    return render(request, 'patients/edit_patient.html', {'form': form, 'patient': patient})

@login_required
@permission_required('patients.view_patient', raise_exception=True)
def patient_dashboard(request, uuid):
    patient = get_object_or_404(
        Patient.objects.visible_to(request.user).select_related('municipio', 'posto_administrativo', 'suco', 'aldeia'),
        uuid=uuid
    )
    
    # Calculate Total Financial Value
    from django.db.models import Sum
    from medical_records.models import Visit
    total_visit_fees = Visit.objects.visible_to(request.user).filter(patient=patient).aggregate(total=Sum('visit_fee'))['total'] or 0
    total_paid = float(patient.registration_fee) + float(total_visit_fees)
    
    return render(request, 'patients/dashboard.html', {
        'patient': patient,
        'total_paid': total_paid,
    })

@login_required
@permission_required('patients.view_patient', raise_exception=True)
def reception_dashboard(request):
    is_hiv = hasattr(request.user, 'staff_profile') and request.user.staff_profile.is_hiv_staff
    query = request.GET.get('q', '').strip()
    patients = []
    if query:
        # Clean the query: strip spaces and convert to upper
        clean_query = query.strip().upper()
        
        base_qs = Patient.objects.visible_to(request.user).select_related(
            'municipio', 'posto_administrativo', 'suco', 'aldeia'
        ).prefetch_related('identities')

        # 1. Exact or Cleaned Patient ID Match
        # Try multiple variations: "PAT-001", "001", etc.
        exact_match = base_qs.filter(
            Q(patient_id__iexact=query) | 
            Q(patient_id__iexact=clean_query)
        ).first()
        
        if exact_match:
            patients.append(exact_match)
        
        # 2. Search by national / other ID number hash (exact match)
        query_hash = hashlib.sha256(clean_query.encode()).hexdigest()
        by_id = PatientID.objects.filter(id_search_hash=query_hash).select_related('patient').first()
        if by_id:
            p = by_id.patient
            if p not in patients:
                patients.append(p)
        
        # 3. Fuzzy search by name, ID, or phone
        # Also try to match digits if the query is something like "PAT-123" -> search for "123"
        numeric_query = ''.join(filter(str.isdigit, clean_query))
        
        fuzzy_query = Q(full_name__icontains=clean_query) | \
                      Q(patient_id__icontains=clean_query) | \
                      Q(phone_number__icontains=clean_query)
        
        if numeric_query:
            fuzzy_query |= Q(patient_id__icontains=numeric_query)

        fuzzy_results = base_qs.filter(fuzzy_query)[:15]
        
        for p in fuzzy_results:
            if p not in patients:
                patients.append(p)
        
        # Apply departmental filtering to search results
        if is_hiv:
            # HIV staff focus only on patients tagged as HIV
            patients = [p for p in patients if p.is_hiv_patient]
        elif not request.user.is_superuser:
            # General staff (non-superusers) only see non-HIV patients
            patients = [p for p in patients if not p.is_hiv_patient]
        # Superusers bypass this filter and see everything
        
        # Limit total results
        patients = patients[:20]
        
        # Check for active (unfinished) visits from previous days
        for p in patients:
            p.pending_visit = Visit.objects.filter(
                patient=p,
                status__in=['SCH', 'IP'],
                visit_date__date__lt=timezone.localdate()
            ).first()
    
    # Today's queue visibility is also isolated
    today_visits = Visit.objects.visible_to(request.user).filter(
        visit_date__date=timezone.localdate()
    ).select_related('patient', 'current_room').order_by('-queue_number')[:200]
    
    return render(request, 'patients/reception.html', {
        'patients': patients,
        'query': query,
        'today_visits': today_visits
    })

@login_required
@permission_required('medical_records.add_visit', raise_exception=True)
def check_in_patient(request, uuid):
    patient = get_object_or_404(Patient.objects.visible_to(request.user), uuid=uuid)
    today = timezone.localdate()
    
    # Check for staff department to determine target room (Smart Routing)
    is_hiv_staff = hasattr(request.user, 'staff_profile') and request.user.staff_profile.is_hiv_staff
    is_emergency_staff = hasattr(request.user, 'staff_profile') and request.user.staff_profile.department.code.upper() in ['IGD', 'EMERGENCY']
    
    if is_hiv_staff and patient.is_hiv_patient:
        dept = 'HIV'
        from medical_records.models import Room
        target_room = Room.objects.filter(code='HIV').first()
    elif is_emergency_staff:
        dept = 'General'
        from medical_records.models import Room
        target_room = Room.objects.filter(code__in=['IGD', 'EMERGENCY']).first()
    else:
        dept = 'General'
        from medical_records.models import Room
        target_room = Room.objects.filter(code='TRIAGE').first() or Room.objects.filter(code='ROOM_2').first()

    # Get or create today's queue for the specific department
    queue, created = DailyQueue.objects.get_or_create(date=today, department=dept)
    queue_number = queue.get_next_number()
    
    # Get visit fee and continuation info
    is_continuation = request.POST.get('is_continuation') == 'true'
    continuation_id = request.POST.get('continuation_of_uuid')
    
    if is_continuation:
        visit_fee = 0.00
    else:
        visit_fee = request.POST.get('visit_fee', 0.00)
        
    patient_type = request.POST.get('patient_type', 'TUAN') # Default to OLD for check-in
    
    # Create Visit
    visit = Visit.objects.create(
        patient=patient,
        queue_number=queue_number,
        status='SCH',
        current_room=target_room,
        visit_fee=visit_fee,
        patient_type=patient_type,
        continuation_of_id=continuation_id if is_continuation else None,
        checked_in_by=request.user,
    )

    # Mark old visit as Uncompleted/Expired if this is a continuation
    if is_continuation and continuation_id:
        Visit.objects.filter(uuid=continuation_id).update(status='UNC')
    
    from medical_records.utils import log_visit_action
    log_visit_action(visit, 'CHECK_IN', request.user, room=target_room)
    
    if is_emergency_staff:
        return redirect('emergency_triage_dashboard')
        
    return redirect('queue_ticket', visit_uuid=visit.uuid)

@login_required
def queue_ticket(request, visit_uuid):
    visit = Visit.objects.get(uuid=visit_uuid)
    return render(request, 'patients/ticket.html', {'visit': visit})

def queue_display(request):
    """Public-facing queue display screen for the waiting room."""
    today = timezone.localdate()
    
    base_qs = Visit.objects.filter(
        visit_date__date=today
    ).exclude(current_room__code='HIV').select_related('patient', 'current_room').order_by('queue_number')
    
    from medical_records.models import Room
    all_rooms = Room.objects.all().order_by('order')
    
    room_data = []
    for room in all_rooms:
        serving = base_qs.filter(current_room=room, status='IP').first()
        waiting = base_qs.filter(current_room=room, status='SCH').order_by('queue_number')
        waiting_list = list(waiting[:5])
        room_data.append({
            'room': room,
            'serving': serving,
            'waiting': waiting_list,
            'waiting_count': waiting.count(),
        })
    
    total_waiting = base_qs.filter(status='SCH').count()
    next_visit = base_qs.filter(status='SCH').first()
    today_visits = base_qs[:300]
    
    return render(request, 'patients/queue_display.html', {
        'today_visits': today_visits,
        'room_data': room_data,
        'next_visit': next_visit,
        'total_waiting': total_waiting,
        'today': today,
    })

# --- Master Data Views ---

@login_required
@permission_required('staff.view_menu_master_data', raise_exception=True)
def master_data_dashboard(request):
    from medical_records.models import Diagnosis
    from staff.models import Department, StaffCategory, Position, StaffProfile
    return render(request, 'master_data/dashboard.html', {
        'municipio_count': Municipio.objects.count(),
        'posto_count': PostoAdministrativo.objects.count(),
        'suco_count': Suco.objects.count(),
        'aldeia_count': Aldeia.objects.count(),
        'patient_count': Patient.objects.visible_to(request.user).count(),
        'diagnosis_count': Diagnosis.objects.count(),
        'staff_count': StaffProfile.objects.count(),
        'dept_count': Department.objects.count(),
        'cat_count': StaffCategory.objects.count(),
        'pos_count': Position.objects.count(),
    })

class PatientListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Patient
    permission_required = 'patients.view_patient'
    template_name = 'master_data/patient_list.html'
    context_object_name = 'patients'
    paginate_by = 25

    def get_queryset(self):
        qs = Patient.objects.visible_to(self.request.user).select_related(
            'municipio', 'posto_administrativo', 'suco', 'aldeia'
        ).only(
            'uuid', 'patient_id', 'full_name', 'gender', 'date_of_birth',
            'address', 'registration_fee', 'is_pregnant', 'is_lactating',
            'municipio__name', 'posto_administrativo__name', 'suco__name', 'aldeia__name',
        )
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(full_name__icontains=q) | Q(patient_id__icontains=q) | Q(phone_number__icontains=q)
            )
        
        # HIV isolation: HIV staff only see HIV patients.
        # Note: Non-HIV staff are already filtered out by Patient.objects.visible_to()
        if not self.request.user.is_superuser:
            if hasattr(self.request.user, 'staff_profile') and self.request.user.staff_profile.is_hiv_staff:
                qs = qs.filter(is_hiv_patient=True)
                
        # Nutrition Filtering
        nutrition_cat = self.request.GET.get('nutrition_cat')
        if nutrition_cat:
            today = timezone.localdate()
            if nutrition_cat == 'baby':
                # 0-6 months (born within last 6 months)
                limit = today - relativedelta(months=6)
                qs = qs.filter(date_of_birth__gt=limit)
            elif nutrition_cat == 'child':
                # 6-59 months (born between 59 and 6 months ago)
                upper = today - relativedelta(months=6)
                lower = today - relativedelta(months=59)
                qs = qs.filter(date_of_birth__lte=upper, date_of_birth__gte=lower)
            elif nutrition_cat == 'bumil':
                qs = qs.filter(is_pregnant=True)
            elif nutrition_cat == 'busui':
                qs = qs.filter(is_lactating=True)

        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['query'] = self.request.GET.get('q', '')
        ctx['total_count'] = Patient.objects.visible_to(self.request.user).count()
        return ctx

class MunicipioListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Municipio
    permission_required = 'patients.view_municipio'
    template_name = 'master_data/list.html'
    context_object_name = 'items'
    extra_context = {'title': 'Municipios', 'model_name': 'municipio'}

class MunicipioDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Municipio
    permission_required = 'patients.view_municipio'
    template_name = 'master_data/detail.html'
    context_object_name = 'item'
    extra_context = {'title': 'Municipio Detail', 'model_name': 'municipio'}

class MunicipioCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Municipio
    permission_required = 'patients.add_municipio'
    fields = ['name']
    template_name = 'master_data/form.html'
    success_url = reverse_lazy('municipio_list')

class MunicipioUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Municipio
    permission_required = 'patients.change_municipio'
    fields = ['name']
    template_name = 'master_data/form.html'
    success_url = reverse_lazy('municipio_list')

class MunicipioDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Municipio
    permission_required = 'patients.delete_municipio'
    template_name = 'master_data/confirm_delete.html'
    success_url = reverse_lazy('municipio_list')

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, _("Cannot delete this Municipio because it is in use by Postos or Patients."))
            return redirect(self.success_url)

# Posto Administrativo CRUD
class PostoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = PostoAdministrativo
    permission_required = 'patients.view_postoadministrativo'
    template_name = 'master_data/list.html'
    context_object_name = 'items'
    extra_context = {'title': 'Postos Administrativos', 'model_name': 'posto'}

class PostoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = PostoAdministrativo
    permission_required = 'patients.view_postoadministrativo'
    template_name = 'master_data/detail.html'
    context_object_name = 'item'
    extra_context = {'title': 'Posto Detail', 'model_name': 'posto'}

class PostoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = PostoAdministrativo
    permission_required = 'patients.add_postoadministrativo'
    fields = ['municipio', 'name']
    template_name = 'master_data/form.html'
    success_url = reverse_lazy('posto_list')

class PostoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = PostoAdministrativo
    permission_required = 'patients.change_postoadministrativo'
    fields = ['municipio', 'name']
    template_name = 'master_data/form.html'
    success_url = reverse_lazy('posto_list')

class PostoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = PostoAdministrativo
    permission_required = 'patients.delete_postoadministrativo'
    template_name = 'master_data/confirm_delete.html'
    success_url = reverse_lazy('posto_list')

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, _("Cannot delete this Posto because it is in use by Sucos or Patients."))
            return redirect(self.success_url)

# Suco CRUD
class SucoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Suco
    permission_required = 'patients.view_suco'
    template_name = 'master_data/list.html'
    context_object_name = 'items'
    extra_context = {'title': 'Sucos', 'model_name': 'suco'}

class SucoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Suco
    permission_required = 'patients.view_suco'
    template_name = 'master_data/detail.html'
    context_object_name = 'item'
    extra_context = {'title': 'Suco Detail', 'model_name': 'suco'}

class SucoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Suco
    permission_required = 'patients.add_suco'
    fields = ['posto', 'name']
    template_name = 'master_data/form.html'
    success_url = reverse_lazy('suco_list')

class SucoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Suco
    permission_required = 'patients.change_suco'
    fields = ['posto', 'name']
    template_name = 'master_data/form.html'
    success_url = reverse_lazy('suco_list')

class SucoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Suco
    permission_required = 'patients.delete_suco'
    template_name = 'master_data/confirm_delete.html'
    success_url = reverse_lazy('suco_list')

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, _("Cannot delete this Suco because it is in use by Aldeias or Patients."))
            return redirect(self.success_url)

# Aldeia CRUD
class AldeiaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Aldeia
    permission_required = 'patients.view_aldeia'
    template_name = 'master_data/list.html'
    context_object_name = 'items'
    extra_context = {'title': 'Aldeias', 'model_name': 'aldeia'}

class AldeiaDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Aldeia
    permission_required = 'patients.view_aldeia'
    template_name = 'master_data/detail.html'
    context_object_name = 'item'
    extra_context = {'title': 'Aldeia Detail', 'model_name': 'aldeia'}

class AldeiaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Aldeia
    permission_required = 'patients.add_aldeia'
    fields = ['suco', 'name']
    template_name = 'master_data/form.html'
    success_url = reverse_lazy('aldeia_list')

class AldeiaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Aldeia
    permission_required = 'patients.change_aldeia'
    fields = ['suco', 'name']
    template_name = 'master_data/form.html'
    success_url = reverse_lazy('aldeia_list')

class AldeiaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Aldeia
    permission_required = 'patients.delete_aldeia'
    template_name = 'master_data/confirm_delete.html'
    success_url = reverse_lazy('aldeia_list')

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, _("Cannot delete this Aldeia because it is in use by Patients."))
            return redirect(self.success_url)

# --- APIs for cascading dropdowns ---

@login_required
def load_postos(request):
    municipio_id = request.GET.get('municipio')
    postos = PostoAdministrativo.objects.filter(municipio_id=municipio_id).order_by('name')
    return JsonResponse(list(postos.values('id', 'name')), safe=False)

@login_required
def load_sucos(request):
    posto_id = request.GET.get('posto')
    sucos = Suco.objects.filter(posto_id=posto_id).order_by('name')
    return JsonResponse(list(sucos.values('id', 'name')), safe=False)

@login_required
def load_aldeias(request):
    suco_id = request.GET.get('suco')
    aldeias = Aldeia.objects.filter(suco_id=suco_id).order_by('name')
    return JsonResponse(list(aldeias.values('id', 'name')), safe=False)
@login_required
def check_duplicates(request):
    """
    AJAX endpoint to check for potential duplicate patients.
    Query params: name, dob, id_number
    """
    name = request.GET.get('name', '').strip()
    dob = request.GET.get('dob', '').strip()
    id_number = request.GET.get('id_number', '').strip()
    
    duplicates = []
    
    # 1. Exact ID check
    if id_number:
        query_hash = hashlib.sha256(id_number.strip().upper().encode()).hexdigest()
        ids = PatientID.objects.filter(id_search_hash=query_hash).select_related('patient')
        for pid in ids:
            p = pid.patient
            duplicates.append({
                'uuid': str(p.uuid),
                'name': p.full_name,
                'dob': str(p.date_of_birth),
                'reason': _('Matching ID Number (%s)') % pid.get_id_type_display()
            })

    # 2. Name + DOB check
    if name and dob:
        similar_patients = Patient.objects.visible_to(request.user).filter(full_name__icontains=name, date_of_birth=dob)
        for p in similar_patients:
            # Avoid adding the same patient twice if they matched ID above
            if not any(d['uuid'] == str(p.uuid) for d in duplicates):
                duplicates.append({
                    'uuid': str(p.uuid),
                    'name': p.full_name,
                    'dob': str(p.date_of_birth),
                    'reason': _('Same Name and Date of Birth')
                })
                
    return JsonResponse({'duplicates': duplicates})

@login_required
def api_patient_search(request):
    """
    Search patients for Select2 AJAX autocomplete.
    """
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    from django.db.models import Q
    patients = Patient.objects.visible_to(request.user).filter(
        Q(full_name__icontains=query) |
        Q(patient_id__icontains=query) |
        Q(phone_number__icontains=query)
    ).order_by('full_name')[:30]
    
    results = []
    for p in patients:
        results.append({
            'id': str(p.uuid),
            'text': f"{p.full_name} ({p.patient_id}) - {p.age} yrs"
        })
    
    return JsonResponse({'results': results})
