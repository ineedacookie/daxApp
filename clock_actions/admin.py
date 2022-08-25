from django.contrib import admin
from .models import TimeActions


class TimeActionsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'type', 'action_datetime', 'comment')
    list_filter = ('id', 'user', 'type', 'action_datetime', 'comment')
    search_fields = ('id', 'type',)
    ordering = ('id',)


admin.site.register(TimeActions, TimeActionsAdmin)
