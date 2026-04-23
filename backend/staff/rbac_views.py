import operator
from functools import reduce

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import Group, Permission
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views import View
from django.db.models import Q
from .models import StaffProfile

class RolePermissionMatrixView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'staff/role_permissions.html'
    permission_required = 'auth.change_group'

    def get(self, request, group_id=None):
        groups = Group.objects.all().order_by('name')
        selected_group = None
        if group_id:
            selected_group = get_object_or_404(Group, id=group_id)

        # Format: (App Label, Model Name, Display Name, [Custom Permission Codenames])
        modules = [
            # --- Core ---
            ('patients', 'patient', 'Patients Management', ['can_print_card', 'can_export_patients', 'view_menu_patients']),
            ('medical_records', 'visit', 'Medical Records / Visits', [
                'can_print_visit', 
                'can_export_visits', 
                'view_menu_medical_records',
                'view_menu_specialist_kia',
                'view_menu_specialist_hiv',
                'view_menu_specialist_tb',
                'view_menu_specialist_dental',
                'view_menu_specialist_nutrition'
            ]),
            ('medical_records', 'room', 'Clinic Rooms', []),
            ('medical_records', 'diagnosis', 'Diagnoses', []),
            ('staff', 'staffprofile', 'Staff Management', ['can_export_staff', 'view_menu_staff', 'view_menu_master_data']),
            ('staff', 'department', 'Departments', []),
            ('staff', 'staffcategory', 'Staff Categories', []),
            ('staff', 'position', 'Positions', []),
            # --- Geography ---
            ('patients', 'municipio', 'Municipios', []),
            ('patients', 'postoadministrativo', 'Postos Administrativos', []),
            ('patients', 'suco', 'Sucos', []),
            ('patients', 'aldeia', 'Aldeias', []),
            # --- Services ---
            ('laboratory', 'labrequest', 'Laboratory Requests', []),
            ('laboratory', 'labresult', 'Laboratory Results', []),
            ('laboratory', 'labtest', 'Lab Tests (Master)', []),
            ('pharmacy', 'medicine', 'Pharmacy - Medicines', []),
            ('pharmacy', 'stockentry', 'Pharmacy - Stock Entries', []),
            ('pharmacy', 'prescription', 'Pharmacy - Prescriptions', []),
            ('radiology', 'radiologyrequest', 'Radiology Requests', []),
            ('radiology', 'radiologyresult', 'Radiology Results', []),
            ('radiology', 'radiologytest', 'Radiology Tests (Master)', []),
            ('pathology', 'pathologyrequest', 'Pathology Requests', []),
            ('pathology', 'pathologyresult', 'Pathology Results', []),
            ('pathology', 'pathologytest', 'Pathology Tests (Master)', []),
            # --- Billing ---
            ('billing', 'invoice', 'Billing - Invoices', ['view_menu_billing', 'can_export_invoices']),
            ('billing', 'payment', 'Billing - Payments', []),
            ('billing', 'servicecategory', 'Billing - Service Categories', []),
            ('billing', 'serviceprice', 'Billing - Service Prices', []),
            ('appointments', 'appointment', 'Appointments', ['view_menu_appointments']),
        ]

        matrix = []
        group_permissions = set()
        if selected_group:
            group_permissions = set(
                selected_group.permissions.select_related('content_type').values_list(
                    'content_type__app_label', 'codename'
                )
            )

        for app_label, model_name, display_name, customs in modules:
            row = {
                'display_name': display_name,
                'app_label': app_label,
                'model_name': model_name,
                'perms': {
                    'view': f'view_{model_name.lower()}',
                    'add': f'add_{model_name.lower()}',
                    'change': f'change_{model_name.lower()}',
                    'delete': f'delete_{model_name.lower()}',
                },
                'customs': []
            }
            
            # Map standard perms to checked status
            for key in ['view', 'add', 'change', 'delete']:
                codename = row['perms'][key]
                row['perms'][key] = {
                    'codename': codename,
                    'checked': (app_label, codename) in group_permissions,
                }
            
            # Map custom perms
            for codename in customs:
                row['customs'].append({
                    'codename': codename,
                    'name': codename.replace('_', ' ').title(),
                    'checked': (app_label, codename) in group_permissions,
                })
            
            matrix.append(row)

        return render(request, self.template_name, {
            'groups': groups,
            'selected_group': selected_group,
            'matrix': matrix,
        })

    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        selected_perms = request.POST.getlist('permissions')
        pairs = []
        for raw in selected_perms:
            parts = raw.split(':', 1)
            if len(parts) == 2 and parts[0] and parts[1]:
                pairs.append((parts[0], parts[1]))
        if not pairs:
            group.permissions.set([])
        else:
            q = reduce(
                operator.or_,
                (Q(content_type__app_label=a, codename=c) for a, c in pairs),
            )
            group.permissions.set(Permission.objects.filter(q))
        
        messages.success(request, f"Permissions updated for role: {group.name}")
        return redirect('role_permissions_selected', group_id=group.id)

class UserRoleMapperView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'staff/user_roles.html'
    permission_required = 'auth.change_user'

    def get(self, request):
        staff_profiles = StaffProfile.objects.all().select_related('user', 'department', 'category')
        all_groups = Group.objects.all().order_by('name')
        
        return render(request, self.template_name, {
            'staff_profiles': staff_profiles,
            'all_groups': all_groups,
        })

    def post(self, request):
        staff_id = request.POST.get('staff_id')
        role_ids = request.POST.getlist('roles')
        
        profile = get_object_or_404(StaffProfile, id=staff_id)
        user = profile.user
        
        # Update user's groups
        groups = Group.objects.filter(id__in=role_ids)
        user.groups.set(groups)
        
        messages.success(request, f"Roles updated for {user.get_full_name() or user.username}")
        return redirect('user_role_assignment')
