from datetime import date, timedelta, datetime

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def grab_begin_date():
    return_date = date.today()
    return return_date - timedelta(days=return_date.weekday())


def grab_expiration_date():
    return_date = date.today()
    return return_date + timedelta(days=30)


class InOutAction(models.Model):
    """Tracks the In and out time actions of users"""
    """Controls all the time actions and keeps them in a nice neat table."""
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, null=False, blank=False)
    start = models.DateTimeField(blank=True, null=True, default=timezone.now)  # the start datetime of the action
    end = models.DateTimeField(blank=True, null=True)  # the end datetime of the action
    total_time = models.FloatField(default=0, null=True,
                                   blank=True)  # the total time of the action, calculated when start and end date are entered.
    type = models.CharField(max_length=1, default="t", choices=(
    ('t', 'Time'), ('b', 'Break'), ('l', 'Lunch')))  # the identifier of if this is time or break.
    start_lon = models.DecimalField(max_digits=22, decimal_places=16, blank=True, null=True)
    start_lat = models.DecimalField(max_digits=22, decimal_places=16, blank=True, null=True)
    end_lon = models.DecimalField(max_digits=22, decimal_places=16, blank=True, null=True)
    end_lat = models.DecimalField(max_digits=22, decimal_places=16, blank=True, null=True)
    comment = models.TextField(blank=True, null=True, default='')
    action_lookup_datetime = models.DateTimeField(blank=True,
                                                  null=True)  # if no end is set then it is the start datetime, otherwise it is the end datetime. For calculating the users current action.
    created_date = models.DateField(_("Created Date"), auto_now_add=True, blank=True)
    updated_date = models.DateField(_("Last Updated Date"), auto_now=True, blank=True)

    def __str__(self):
        return self.user.__str__() + ", " + self.type.__str__() + ", " + self.start.__str__() + ', ' + self.end.__str__()

    def save(self, *args, **kwargs):
        """Overridden to allow for calling update current time action after a time action is edited or created"""
        # set action_lookup_datetime when necessary
        if 'skip' in kwargs:
            skip = kwargs.pop('skip')
        else:
            skip = False
        super(InOutAction, self).save(*args, **kwargs)
        if not skip:
            if self.end:
                self.action_lookup_datetime = self.end
            else:
                self.action_lookup_datetime = self.start
            if self.end and self.start:
                self.total_time = self.end.timestamp() - self.start.timestamp()
            else:
                self.total_time = 0
            self.save(skip=True)
            self.update_current_time_action()

    def delete(self, *args, **kwargs):
        """Overridden to allow for calling update current time action after deletion"""
        super(InOutAction, self).delete(*args, **kwargs)
        self.update_current_time_action()

    def update_current_time_action(self):
        """Updates the current time action attached to the specific user"""
        if self.user:
            current_action = \
                InOutAction.objects.filter(user=self.user).filter(type=self.type).filter(
                    action_lookup_datetime__lte=timezone.now()).order_by(
                    '-action_lookup_datetime')[0]
            user_info = TTUserInfo.objects.filter(user=self.user)[0]
            if self.type == 't':
                user_info.time_action = current_action
            elif self.type == 'b':
                user_info.break_action = current_action
            user_info.update_status()
            user_info.save()


class TTCompanyInfo(models.Model):
    """Tracks the company information used for the time_tracker"""
    company = models.ForeignKey('users.Company', on_delete=models.CASCADE, null=False, blank=False)
    pay_period_type = models.CharField(max_length=1, help_text="Pay period type", default="w", blank=False, choices=(
        ('w', 'Weekly'), ('b', 'Bi-Weekly'), ('s', 'Semi-Monthly'), ('m', 'Monthly')))
    period_begin_date = models.DateField(default=grab_begin_date, blank=False)
    week_start_day = models.IntegerField(default=0, blank=False, choices=(
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'),
        (6, 'Sunday')))
    default_weekly_overtime = models.BooleanField(default=True)
    default_weekly_overtime_value = models.IntegerField(default=40, validators=[MaxValueValidator(120), MinValueValidator(0)],
                                                blank=True)
    default_daily_overtime = models.BooleanField(default=False)
    default_daily_overtime_value = models.IntegerField(default=8, validators=[MaxValueValidator(23), MinValueValidator(0)],
                                               blank=True)
    default_double_time = models.BooleanField(default=False)
    default_double_time_value = models.IntegerField(default=12, validators=[MaxValueValidator(23), MinValueValidator(1)],
                                            blank=True)
    default_california_overtime = models.BooleanField(default=False)
    default_enable_breaks = models.BooleanField(default=True)
    default_breaks_are_paid = models.BooleanField(default=False, blank=True)
    default_include_breaks_in_overtime_calculation = models.BooleanField(default=False, blank=True)
    use_company_defaults_for_all_employees = models.BooleanField(default=False, blank=True)
    display_employee_times_with_timezone = models.BooleanField(default=False, blank=True)
    created_date = models.DateField(_("Created Date"), auto_now_add=True, blank=True)
    updated_date = models.DateField(_("Updated Date"), auto_now=True, blank=True, null=True)

    def __str__(self):
        return self.company.name


class TTUserInfo(models.Model):
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, null=False, blank=False)
    time_action = models.ForeignKey(InOutAction, related_name='+', on_delete=models.SET_NULL, default=None,
                                    null=True,
                                    blank=True)
    break_action = models.ForeignKey(InOutAction, related_name='+', on_delete=models.SET_NULL, default=None,
                                    null=True,
                                    blank=True)
    status_text = models.CharField(max_length=1, default="n", choices=(
    ('i', 'Clocked In'), ('o', 'Clocked Out'), ('b', 'On Break'), ('c', 'Back From Break'), ('n', 'Welcome to DaxApp')), null=True, blank=True)
    status_time = models.DateTimeField(blank=True, null=True)
    use_company_default_overtime_settings = models.BooleanField(default=True, null=True, blank=True)
    weekly_overtime = models.BooleanField(default=None, null=True, blank=True)
    weekly_overtime_value = models.IntegerField(default=None,
                                                        validators=[MaxValueValidator(120), MinValueValidator(0)],
                                                        blank=True, null=True)
    daily_overtime = models.BooleanField(default=None)
    daily_overtime_value = models.IntegerField(default=None,
                                                       validators=[MaxValueValidator(23), MinValueValidator(0)],
                                                       blank=True, null=True)
    double_time = models.BooleanField(default=None, null=True, blank=True)
    double_time_value = models.IntegerField(default=None,
                                                    validators=[MaxValueValidator(23), MinValueValidator(1)],
                                                    blank=True, null=True)
    california_overtime = models.BooleanField(default=False)
    use_company_default_break_settings = models.BooleanField(default=True, null=True, blank=True)
    enable_breaks = models.BooleanField(default=None, null=True, blank=True)
    breaks_are_paid = models.BooleanField(default=None, blank=True, null=True)
    include_breaks_in_overtime_calculation = models.BooleanField(default=None, blank=True, null=True)
    created_date = models.DateField(_("Created Date"), auto_now_add=True, blank=True, null=True)
    updated_date = models.DateField(_("Updated Date"), auto_now=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        created = not self.pk
        if created:
            tt_company = TTCompanyInfo.objects.filter(company=self.user.company)
            if tt_company:
                tt_company = tt_company[0]
                for i in ['weekly_overtime', 'weekly_overtime_value', 'daily_overtime', 'daily_overtime_value', 'double_time', 'double_time_value',
                          'california_overtime', 'enable_breaks', 'breaks_are_paid', 'include_breaks_in_overtime_calculation']:
                    if getattr(self, i) is None:
                        setattr(self, i, getattr(tt_company, 'default_' + i))
        super().save(*args, **kwargs)

    def update_status(self):
        if self.time_action and self.break_action:
            if self.time_action.end:
                self.status_text = 'o'
                self.status_time = self.time_action.end
            elif self.break_action.end and self.break_action.end > self.time_action.start:
                self.status_text = 'c'
                self.status_time = self.break_action.end
            elif self.break_action.start and self.break_action.start > self.time_action.start:
                self.status_text = 'b'
                self.status_time = self.break_action.start
            else:
                self.status_text = 'i'
                self.status_time = self.time_action.start
        elif self.time_action:
            if self.time_action.end:
                self.status_text = 'o'
                self.status_time = self.time_action.end
            else:
                self.status_text = 'i'
                self.status_time = self.time_action.start
        else:
            self.status_text = 'n'
            self.status_time = None


class TTReports(models.Model):
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, null=False, blank=False)
    custom_name = models.CharField(max_length=250, default='', blank=True, null=True)
    report_name = models.TextField(default='', blank=False, null=False)
    folder = models.CharField(max_length=250, default='detailed', blank=False, null=False)
    expiration_date = models.DateField(default=grab_begin_date, blank=False)
    created_date = models.DateField(_("Created Date"), auto_now_add=True, blank=True, null=True)


    def report_path(self):
        date_time = str(datetime.now())
        name = ''
        if self.custom_name:
            name = self.custom_name + '_' + date_time
        else:
            name = self.report_name + '_' + date_time
        return '/'.join(['reports', str(self.user.id), self.folder, name + '.pdf'])