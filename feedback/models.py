from django.db import models
from django.utils.translation import gettext_lazy as _


class Feedback(models.Model):
    user = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    type = models.CharField(max_length=1, choices=(('f', 'Feature Request'), ('e', 'Error'), ('r', 'Review')))
    subject = models.CharField(max_length=500)
    content = models.TextField()
    created_date = models.DateField(_("Date"), auto_now_add=True, blank=True)

    def __str__(self):
        return self.subject