from django.contrib import admin


class FeedbackAdmin(admin.ModelAdmin):
    change_form_template = 'tc_admin/change_form.html'
    list_display = ('id', 'user', 'type', 'subject', 'created_date')
    list_filter = ('type', 'user', 'created_date')
    search_fields = ('user', 'subject',)
    ordering = ('-id',)

    class Media:
        pass
