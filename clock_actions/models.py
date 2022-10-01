from django.db import models
from django.utils import timezone
from users.models import CustomUser  # this is correct syntax
from django.utils.translation import gettext_lazy as _


class InOutTimeActions(models.Model):
    """Controls all the time actions and keeps them in a nice neat table."""
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, null=True, blank=True)
    start = models.DateTimeField(blank=True, null=True, default=timezone.now) # the start datetime of the action
    end = models.DateTimeField(blank=True, null=True)   # the end datetime of the action
    total_time = models.FloatField(default=0, null=True, blank=True)    # the total time of the action, calculated when start and end date are entered.
    type = models.CharField(max_length=1, default="t", choices=(('t', 'Time'), ('b', 'Break'), ('l', 'Lunch'))) # the identifier of if this is time or break.
    start_lon = models.DecimalField(max_digits=22, decimal_places=16, blank=True, null=True)
    start_lat = models.DecimalField(max_digits=22, decimal_places=16, blank=True, null=True)
    end_lon = models.DecimalField(max_digits=22, decimal_places=16, blank=True, null=True)
    end_lat = models.DecimalField(max_digits=22, decimal_places=16, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    date = models.DateField(_("Date"), blank=True, null=True, default=timezone.now) # the date that this action should be applied to.
    action_lookup_datetime = models.DateTimeField(blank=True, null=True)    # if no end is set then it is the start datetime, otherwise it is the end datetime. For calculating the users current action.
    created_date = models.DateField(_("Created Date"), auto_now_add=True, blank=True)
    updated_date = models.DateField(_("Last Updated Date"), auto_now=True, blank=True)

    def __str__(self):
        return self.user.__str__() + ", " + self.type.__str__() + ", " + self.start.__str__() + ', ' + self.end.__str__()

    def save(self, *args, **kwargs):
        """Overridden to allow for calling update current time action after a time action is edited or created"""
        # set action_lookup_datetime when necessary
        super(InOutTimeActions, self).save(*args, **kwargs)
        if self.end:
            self.action_lookup_datetime = self.end
        else:
            self.action_lookup_datetime = self.start
        if self.end and self.start:
            self.total_time = self.end.timestamp() - self.start.timestamp()
        else:
            self.total_time = 0
        self.date = self.start.date()
        self.save()
        self.update_current_time_action()

    def delete(self, *args, **kwargs):
        """Overridden to allow for calling update current time action after deletion"""
        super(InOutTimeActions, self).delete(*args, **kwargs)
        self.update_current_time_action()

    def update_current_time_action(self):
        """Updates the current time action attached to the specific user"""
        if self.user:
            current_action = \
                InOutTimeActions.objects.filter(user=self.user).filter(action_lookup_datetime__lt=timezone.now()).order_by(
                    '-action_lookup_datetime')[0]
            action_to_update = CustomUser.objects.filter(id=self.user.id)[0]
            action_to_update.time_action = current_action
            action_to_update.save()


class TTActions(models.Model):
    """Controls all the time actions and keeps them in a nice neat table."""
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, null=True, blank=True)
    total_time = models.FloatField(default=0, null=True, blank=True)
    type = models.CharField(max_length=1, help_text="Pay period type", default="w",
                            choices=(('i', 'Clock In'), ('o', 'Clock Out'), ('b', 'Begin Break'), ('e', 'End Break')))
    comment = models.TextField(blank=True, null=True)
    date = models.DateField(_("Date"), blank=False, null=False)
    created_date = models.DateField(_("Created Date"), auto_now_add=True, blank=True)
    updated_date = models.DateField(_("Last Updated Date"), auto_now=True, blank=True)
