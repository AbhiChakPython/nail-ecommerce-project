from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms
from .models import CustomUser, CustomerAddress


class AdminUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'full_name', 'role')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'full_name', 'phone_number',
            'role', 'is_active', 'is_staff', 'is_superuser',
            'groups', 'user_permissions'
        )


# ✅ Define Inline Before UserAdmin
class CustomerAddressInline(admin.StackedInline):
    model = CustomerAddress
    can_delete = False
    verbose_name_plural = 'Customer Address'
    fk_name = 'user'


class UserAdmin(BaseUserAdmin):
    model = CustomUser
    form = UserChangeForm
    add_form = AdminUserCreationForm

    inlines = (CustomerAddressInline,)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

    list_display = ('username', 'email', 'full_name', 'role', 'is_staff', 'is_active', 'date_joined', 'last_login')
    list_filter = ('role', 'is_staff', 'is_active')
    readonly_fields = ('last_login', 'date_joined')

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'phone_number')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'full_name', 'role', 'password1', 'password2', 'is_staff', 'is_active')}
         ),
    )
    search_fields = ('username', 'email', 'full_name')
    ordering = ('-date_joined', 'username',)
    filter_horizontal = ('groups', 'user_permissions')


class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'address_line1', 'city', 'pincode', 'use_for_home_service')
    search_fields = ('user__username', 'city', 'pincode')
    list_filter = ('city', 'state', 'use_for_home_service')


# ✅ Register models separately
admin.site.register(CustomUser, UserAdmin)
admin.site.register(CustomerAddress, CustomerAddressAdmin)
