from django.contrib import admin
from .models import InOutTimeActions


class InOutTimeActionsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'type', 'start', 'end', 'comment')
    list_filter = ('id', 'user', 'type', 'start', 'end', 'comment')
    search_fields = ('id', 'type',)
    ordering = ('id',)


admin.site.register(InOutTimeActions, InOutTimeActionsAdmin)
