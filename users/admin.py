from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from admin_auto_filters.filters import AutocompleteFilter

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser, Company, CompanyConnection


class CompanyFilter(AutocompleteFilter):
    title = 'Company'
    field_name = 'company'


class UserFilter(AutocompleteFilter):
    title = 'User'
    field_name = 'user'


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    list_display = ('email', 'company', 'is_active', 'created_date')
    list_filter = (CompanyFilter, 'is_active', 'created_date', 'is_staff')
    fieldsets = (
        (None, {'fields': (
        'company', 'email', 'password', 'first_name', 'middle_name', 'last_name', 'change_email', 'timezone',
        'verified')}),
        ('Permissions', {'fields': ('is_active', 'is_staff')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
            'company', 'email', 'first_name', 'middle_name', 'last_name', 'timezone',
            'verified', 'password1', 'password2', 'is_staff', 'is_active')}
         ),
    )
    search_fields = ('email',)
    autocomplete_fields = ('company', )
    ordering = ('email',)

    class Media:
        pass


class CompanyAdmin(admin.ModelAdmin):
    change_form_template = 'io_admin/change_form.html'
    list_display = ('id', 'name', 'created_date')
    list_filter = ('id', 'name', 'paying', 'created_date')
    search_fields = ('name',)
    ordering = ('-id',)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['id'] = object_id
        extra_context['company'] = True
        return super(CompanyAdmin, self).change_view(
            request, object_id, form_url, extra_context=extra_context,
        )


class CompanyConnectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'user', 'role', 'updated_date')
    list_filter = (CompanyFilter, UserFilter, 'role', 'updated_date')
    search_fields = ('id',)
    ordering = ('company', 'user')


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Company, CompanyAdmin)
admin.site.register(CompanyConnection, CompanyConnectionAdmin)
admin.site.unregister(Group)
