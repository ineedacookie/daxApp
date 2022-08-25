from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from admin_auto_filters.filters import AutocompleteFilter

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser, Company


class CompanyFilter(AutocompleteFilter):
    title = 'Company'
    field_name = 'company'


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    list_display = ('email', 'company', 'is_staff', 'is_active', 'time_action', 'created_date')
    list_filter = (CompanyFilter, 'is_staff', 'is_active', 'created_date')
    fieldsets = (
        (None, {'fields': (
        'email', 'password', 'first_name', 'middle_name', 'last_name', 'role', 'theme', 'wp_id', 'timezone',
        'verified', 'time_action', 'pay_rate')}),
        ('Permissions', {'fields': ('is_staff', 'is_active')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
            'company', 'email', 'first_name', 'middle_name', 'last_name', 'role', 'theme', 'wp_id', 'timezone',
            'verified', 'password1', 'password2', 'pay_rate', 'is_staff', 'is_active')}
         ),
    )
    search_fields = ('email',)
    autocomplete_fields = ('company', )
    ordering = ('email',)

    class Media:
        pass


class CompanyAdmin(admin.ModelAdmin):
    change_form_template = 'io_admin/change_form.html'
    list_display = ('id', 'name', 'last_renew_date', 'created_date')
    list_filter = ('id', 'name', 'last_renew_date', 'created_date')
    search_fields = ('name',)
    ordering = ('-id',)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['id'] = object_id
        extra_context['company'] = True
        return super(CompanyAdmin, self).change_view(
            request, object_id, form_url, extra_context=extra_context,
        )


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Company, CompanyAdmin)
admin.site.unregister(Group)
