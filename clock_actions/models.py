from django.db import models
from django.utils import timezone
from users.models import CustomUser  # this is correct syntax


class TimeActions(models.Model):
    """Controls all of the time actions and keeps them in a nice neat table."""
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=1, help_text="Pay period type", default="w",
                            choices=(('i', 'Clock In'), ('o', 'Clock Out'), ('b', 'Begin Break'), ('e', 'End Break')))
    action_datetime = models.DateTimeField(default=timezone.now, blank=True, null=True)
    lon = models.DecimalField(max_digits=22, decimal_places=16, blank=True, null=True)
    lat = models.DecimalField(max_digits=22, decimal_places=16, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.__str__() + ", " + self.type.__str__() + ", " + self.action_datetime.__str__()

    def save(self, *args, **kwargs):
        """Overridden to allow for calling update current time action after a time action is edited or created"""
        super(TimeActions, self).save(*args, **kwargs)
        self.update_current_time_action()

    def delete(self, *args, **kwargs):
        """Overridden to allow for calling update current time action after deletion"""
        super(TimeActions, self).delete(*args, **kwargs)
        self.update_current_time_action()

    def update_current_time_action(self):
        """Updates the current time action attached to the specific user"""
        if self.user:
            current_action = \
                TimeActions.objects.filter(user=self.user).filter(action_datetime__lt=timezone.now()).order_by(
                    '-action_datetime')[0]
            action_to_update = CustomUser.objects.filter(id=self.user.id)[0]
            action_to_update.time_action = current_action
            action_to_update.save()
