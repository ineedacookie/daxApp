from django.contrib import admin
from .models import InOutAction
from admin_auto_filters.filters import AutocompleteFilter


class UserFilter(AutocompleteFilter):
    title = 'User'
    field_name = 'user'


class InOutActionsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'type', 'start', 'end', 'comment')
    list_filter = ('id', UserFilter, 'type', 'start', 'end', 'comment')
    search_fields = ('id',)
    ordering = ('id',)


admin.site.register(InOutAction, InOutActionsAdmin)