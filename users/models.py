from datetime import date, timedelta

from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from timezone_field import TimeZoneField

from .managers import CustomUserManager


def grab_begin_date():
    return_date = date.today()
    return return_date - timedelta(days=return_date.weekday())


class Company(models.Model):
    name = models.CharField(max_length=255, help_text="Company Name", blank=False)
    pay_period_type = models.CharField(max_length=1, help_text="Pay period type", default="w", blank=False, choices=(
        ('w', 'Weekly'), ('b', 'Bi-Weekly'), ('s', 'Semi-Monthly'), ('m', 'Monthly')))
    period_begin_date = models.DateField(default=grab_begin_date, blank=False)
    week_start_day = models.IntegerField(default=0, blank=False, choices=(
    (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')))
    weekly_overtime = models.BooleanField(default=True)
    weekly_overtime_value = models.IntegerField(default=40, validators=[MaxValueValidator(120), MinValueValidator(0)],
                                                blank=True)
    daily_overtime = models.BooleanField(default=False)
    daily_overtime_value = models.IntegerField(default=8, validators=[MaxValueValidator(23), MinValueValidator(0)],
                                               blank=True)
    double_time = models.BooleanField(default=False)
    double_time_value = models.IntegerField(default=12, validators=[MaxValueValidator(23), MinValueValidator(1)],
                                            blank=True)
    enable_breaks = models.BooleanField(default=True)
    breaks_are_paid = models.BooleanField(default=False, blank=True)
    include_breaks_in_overtime_calculation = models.BooleanField(default=False, blank=True)
    timezone = TimeZoneField(choices_display='WITH_GMT_OFFSET', null=True, use_pytz=True)
    default_theme = models.IntegerField(blank=True, null=True)
    last_renew_date = models.DateField(blank=True, null=True)
    use_company_timezone = models.BooleanField(default=False, blank=True)
    display_employee_times_with_timezone = models.BooleanField(default=False, blank=True)
    created_date = models.DateField(_("Date"), auto_now_add=True, blank=True)

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    username = None
    email = models.EmailField(_('email address'), unique=True)
    change_email = models.EmailField(null=True, blank=True, default=None)
    first_name = models.CharField(max_length=50, help_text="Employees First Name", blank=False, null=True)
    middle_name = models.CharField(max_length=50, help_text="Employees Middle Name", blank=True, null=True)
    last_name = models.CharField(max_length=100, help_text="Employees Last Name", blank=False, null=True)
    role = models.CharField(max_length=1, help_text="The role of the user within the company", null=True, default="e",
                            blank=True, choices=(('e', 'Employee'), ('c', 'Company Admin'), ('r', 'Restricted Admin')))
    pay_rate = models.DecimalField(decimal_places=2, max_digits=6, blank=False, default=0)
    theme = models.IntegerField(default=1, blank=True, null=True)
    wp_id = models.CharField(max_length=50, help_text="Wordpress ID", blank=True, null=True)
    timezone = TimeZoneField(choices_display='WITH_GMT_OFFSET', null=True, use_pytz=True)
    verified = models.BooleanField(default=False, blank=True, null=True)
    created_date = models.DateField(_("Date"), auto_now_add=True, blank=True, null=True)
    time_action = models.ForeignKey('clock_actions.TimeActions', on_delete=models.SET_NULL, default=None, null=True,
                                    blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

