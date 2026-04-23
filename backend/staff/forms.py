from django import forms
from django.contrib.auth.models import User, Group
from django.utils.translation import gettext_lazy as _
from .models import StaffProfile

class IntegratedStaffForm(forms.ModelForm):
    # User fields
    username = forms.CharField(max_length=150, label=_("Username"))
    password = forms.CharField(widget=forms.PasswordInput(), label=_("Password"))
    first_name = forms.CharField(max_length=150, label=_("First Name"))
    last_name = forms.CharField(max_length=150, label=_("Last Name"))
    email = forms.EmailField(label=_("Email"))
    
    # Selection for Groups (Roles)
    roles = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_("Assign Roles")
    )

    class Meta:
        model = StaffProfile
        fields = ['department', 'category', 'position', 'phone', 'address', 'bio', 'photo', 'is_active']

    @staticmethod
    def _generate_staff_id():
        last = StaffProfile.objects.order_by('-staff_id').first()
        if last and last.staff_id.startswith('CLB'):
            try:
                seq = int(last.staff_id[3:]) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1
        return f"CLB{seq:04d}"

    def save(self, commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
            email=self.cleaned_data['email'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name']
        )
        
        user.groups.set(self.cleaned_data['roles'])
        
        profile = super().save(commit=False)
        profile.user = user
        profile.staff_id = self._generate_staff_id()
        
        if commit:
            profile.save()
        return profile

class StaffUpdateForm(forms.ModelForm):
    class Meta:
        model = StaffProfile
        fields = ['staff_id', 'department', 'category', 'position', 'phone', 'address', 'bio', 'photo', 'is_active']
