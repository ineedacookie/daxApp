from django import forms
from django.forms import HiddenInput, ModelForm, CharField, Form, DateInput
from users.models import CustomUser  # this is correct syntax


from .models import InOutAction


class SimpleClockForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ModelForm, self).__init__(*args, **kwargs)

    class Meta:
        model = InOutAction
        fields = ('user', 'type', 'start', 'end', 'comment')