from django.contrib.auth.models import Group
from django.contrib.auth import logout as auth_logout
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.db.models import ProtectedError
from django.utils.translation import gettext_lazy as _
from .models import Department, StaffCategory, Position, StaffProfile
from .forms import IntegratedStaffForm, StaffUpdateForm

# --- Department CRUD ---
class DepartmentListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Department
    permission_required = 'staff.view_department'
    template_name = 'staff/department_list.html'
    context_object_name = 'items'

class DepartmentCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Department
    permission_required = 'staff.add_department'
    fields = ['name', 'code', 'description', 'is_active']
    template_name = 'staff/form.html'
    success_url = reverse_lazy('department_list')
    extra_context = {'title': _('Create Department')}

class DepartmentUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Department
    permission_required = 'staff.change_department'
    fields = ['name', 'code', 'description', 'is_active']
    template_name = 'staff/form.html'
    success_url = reverse_lazy('department_list')
    extra_context = {'title': _('Edit Department')}

class DepartmentDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Department
    permission_required = 'staff.delete_department'
    template_name = 'staff/confirm_delete.html'
    success_url = reverse_lazy('department_list')

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, _("Cannot delete this Department because it is in use by Staff members."))
            return redirect(self.success_url)

# --- Staff Category CRUD ---
class StaffCategoryListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = StaffCategory
    permission_required = 'staff.view_staffcategory'
    template_name = 'staff/category_list.html'
    context_object_name = 'items'

class StaffCategoryCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = StaffCategory
    permission_required = 'staff.add_staffcategory'
    fields = ['name', 'description']
    template_name = 'staff/form.html'
    success_url = reverse_lazy('category_list')
    extra_context = {'title': _('Create Staff Category')}

class StaffCategoryUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = StaffCategory
    permission_required = 'staff.change_staffcategory'
    fields = ['name', 'description']
    template_name = 'staff/form.html'
    success_url = reverse_lazy('category_list')
    extra_context = {'title': _('Edit Staff Category')}

# --- Position CRUD ---
class PositionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Position
    permission_required = 'staff.view_position'
    template_name = 'staff/position_list.html'
    context_object_name = 'items'

class PositionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Position
    permission_required = 'staff.add_position'
    fields = ['name', 'description']
    template_name = 'staff/form.html'
    success_url = reverse_lazy('position_list')
    extra_context = {'title': _('Create Position')}

class PositionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Position
    permission_required = 'staff.change_position'
    fields = ['name', 'description']
    template_name = 'staff/form.html'
    success_url = reverse_lazy('position_list')
    extra_context = {'title': _('Edit Position')}

class PositionDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Position
    permission_required = 'staff.delete_position'
    template_name = 'staff/confirm_delete.html'
    success_url = reverse_lazy('position_list')

# --- Staff Profile CRUD ---
class StaffListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = StaffProfile
    permission_required = 'staff.view_staffprofile'
    template_name = 'staff/staff_list.html'
    context_object_name = 'items'

class StaffCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = StaffProfile
    form_class = IntegratedStaffForm
    permission_required = 'staff.add_staffprofile'
    template_name = 'staff/staff_form.html'
    success_url = reverse_lazy('staff_list')
    extra_context = {'title': _('Register New Staff & Create User')}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Staff member and User account created successfully."))
        return response

class StaffUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = StaffProfile
    form_class = StaffUpdateForm
    permission_required = 'staff.change_staffprofile'
    template_name = 'staff/form.html'
    success_url = reverse_lazy('staff_list')
    extra_context = {'title': _('Edit Staff Profile')}

# --- Custom Logout Handle (Support GET for convenience) ---
def custom_logout(request):
    auth_logout(request)
    messages.success(request, _("You have been logged out successfully."))
    return redirect('login')

# --- Role CRUD (Django Group) ---
class RoleListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Group
    template_name = 'staff/role_list.html'
    context_object_name = 'items'
    permission_required = 'auth.view_group'
    ordering = ['name']

class RoleCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Group
    fields = ['name']
    template_name = 'staff/form.html'
    success_url = reverse_lazy('role_list')
    permission_required = 'auth.add_group'
    extra_context = {'title': _('Create New Role')}

    def form_valid(self, form):
        messages.success(self.request, _("Role created successfully."))
        return super().form_valid(form)

class RoleUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Group
    fields = ['name']
    template_name = 'staff/form.html'
    success_url = reverse_lazy('role_list')
    permission_required = 'auth.change_group'
    extra_context = {'title': _('Edit Role')}

    def form_valid(self, form):
        messages.success(self.request, _("Role updated successfully."))
        return super().form_valid(form)

class RoleDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Group
    template_name = 'staff/confirm_delete.html'
    success_url = reverse_lazy('role_list')
    permission_required = 'auth.delete_group'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _("Role deleted successfully."))
        return super().delete(request, *args, **kwargs)
