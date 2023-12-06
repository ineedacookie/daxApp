from datetime import date, timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from timezone_field import TimeZoneField
from time_tracker.models import TTUserInfo, TTCompanyInfo

from .managers import CustomUserManager


class Company(models.Model):
    name = models.CharField(max_length=255, help_text="Company Name", blank=True, null=True)
    timezone = TimeZoneField(choices_display='WITH_GMT_OFFSET', null=True)
    use_company_timezone = models.BooleanField(default=False, blank=True)
    paying = models.BooleanField(default=False, blank=True)
    created_date = models.DateField(_("Created Date"), auto_now_add=True, blank=True)
    updated_date = models.DateField(_("Updated Date"), auto_now=True, blank=True, null=True)

    def __str__(self):
        return str(self.name) + ' #' + str(self.pk)

    def save(self, *args, **kwargs):
        """Overridding so that we can create other necessary models off of this one. Like TTCompany Info for time tracking."""
        created = not self.pk
        super().save(*args, **kwargs)
        if created:
            # this is created for the first time, so we need to initialize other modals
            TTCompanyInfo.objects.create(company=self)


class CustomUser(AbstractUser):
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    username = None
    email = models.EmailField(_('Email'), unique=True)
    change_email = models.EmailField(null=True, blank=True, default=None)
    first_name = models.CharField(_('First Name'), max_length=50, blank=True, null=True)
    middle_name = models.CharField(_('Middle Name'), max_length=50, blank=True, null=True)
    last_name = models.CharField(_('Last Name'), max_length=100, blank=True, null=True)
    timezone = TimeZoneField(choices_display='WITH_GMT_OFFSET', null=True, blank=True, use_pytz=True)
    verified = models.BooleanField(default=False, blank=True)
    created_date = models.DateField(_("Created Date"), auto_now_add=True, blank=True, null=True)
    updated_date = models.DateField(_("Updated Date"), auto_now=True, blank=True, null=True)
    full_name = models.CharField(_('Full Name'), max_length=200, blank=True, null=True, default=None)
    active = models.BooleanField(_('Active'), blank=True, null=True, default=True)
    marked_for_deletion = models.DateField(null=True, blank=True)     # added this to allow for a 30 day grace period before deleting the user perminately.

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        created = not self.pk
        self.update_full_name()
        super().save(*args, **kwargs)
        if not self.company:
            # This is the first instance of this employee lets give them a company if they don't already have one.
            company = Company.objects.create()
            CompanyConnection.objects.create(company=company, user=self, role='c')
            self.company = company
        if created:
            TTUserInfo.objects.create(user=self)

    def update_full_name(self):
        """
        Stores the full name as last_name, first_name middle_name.
        """
        if self.first_name and self.last_name:
            text = self.last_name + ', ' + self.first_name
            if self.middle_name:
                text += ' ' + self.middle_name
        else:
            text = ''
        self.full_name = text.upper()


class CompanyConnection(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=False)
    role = models.CharField(_('Role'), max_length=2, help_text="The role of the user within the company", default='e', choices=(('e', 'Employee'), ('c', 'Company Admin'), ('r', 'Restricted Admin')))
    updated_date = models.DateField(_("Updated Date"), auto_now=True, blank=True, null=True)


class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=False)
    type = models.CharField(_('Type'), max_length=50, blank=False, null=False, default='default')
    message = models.TextField(blank=False, null=False)
    link = models.TextField(blank=True, null=True)
    created_date = models.DateField(_("Created Date"), auto_now_add=True, blank=True, null=True)