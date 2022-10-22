from datetime import date, timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from timezone_field import TimeZoneField

from .managers import CustomUserManager


class Company(models.Model):
    name = models.CharField(max_length=255, help_text="Company Name", blank=False)
    timezone = TimeZoneField(choices_display='WITH_GMT_OFFSET', null=True, use_pytz=True)
    default_theme = models.IntegerField(blank=True, null=True)
    use_company_timezone = models.BooleanField(default=False, blank=True)
    created_date = models.DateField(_("Date"), auto_now_add=True, blank=True)

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    username = None
    email = models.EmailField(_('Email'), unique=True)
    change_email = models.EmailField(null=True, blank=True, default=None)
    first_name = models.CharField(_('First Name'), max_length=50, blank=False, null=True)
    middle_name = models.CharField(_('Middle Name'), max_length=50, blank=True, null=True)
    last_name = models.CharField(_('Last Name'), max_length=100, blank=False, null=True)
    theme = models.IntegerField(default=1, blank=True, null=True)
    timezone = TimeZoneField(choices_display='WITH_GMT_OFFSET', null=True, blank=True, use_pytz=True)
    verified = models.BooleanField(default=False, blank=True, null=True)
    created_date = models.DateField(_("Date"), auto_now_add=True, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class CompanyConnection(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=False)
    role = models.CharField(_('Role'), max_length=2, help_text="The role of the user within the company", default='e', choices=(('e', 'Employee'), ('c', 'Company Admin'), ('r', 'Restricted Admin')))


